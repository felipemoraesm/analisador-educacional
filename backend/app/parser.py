"""Analisador sintático (parser) do subconjunto de C: descendente recursivo.

Estratégia
- Cada não terminal da gramática (``app/gramatica.py``) vira um método.
- Escrito à mão, sem geradores: o aluno enxerga a correspondência direta entre
  a regra EBNF e o código, o que facilita explicar o funcionamento.
- Recebe a lista de tokens do scanner (Etapa 3) e devolve a AST, ou os erros
  sintáticos (nunca os dois).
- Precedência e associatividade vêm da própria estrutura da gramática: um
  método por nível (``||`` < ``&&`` < igualdade < relacional < ``+ -`` < ``* / %``
  < unários), com laços para a associatividade à esquerda.
- Recuperação de erros em modo pânico: após um erro, descarta tokens até um
  ponto seguro (``;``, ``}`` ou início de instrução) e continua, acumulando
  vários erros sem repetir o mesmo problema em cascata.

Limites de segurança: no máximo ``LIMITE_ERROS`` erros, ``LIMITE_ANINHAMENTO``
níveis de aninhamento e ``LIMITE_ALTURA`` níveis de altura da árvore.
"""

from typing import Dict, List, Optional

from .gramatica import NOS, regras_dos_tipos

LIMITE_ERROS = 10
LIMITE_ANINHAMENTO = 40
LIMITE_ALTURA = 120
LIMITE_NOS_TEXTO = 1000

TIPOS_DADO = ("int", "float", "char")
TIPOS_RETORNO = TIPOS_DADO + ("void",)
NIVEIS = (("||",), ("&&",), ("==", "!="), ("<", ">", "<=", ">="), ("+", "-"), ("*", "/", "%"))
TIPO_ARITMETICO = {"+": "ADICAO", "-": "SUBTRACAO", "*": "MULTIPLICACAO", "/": "DIVISAO", "%": "MODULO"}
LITERAIS = ("LITERAL_INTEIRO", "LITERAL_REAL", "LITERAL_STRING", "LITERAL_CHAR")
INICIO_EXPRESSAO = ["IDENTIFICADOR", "LITERAL_INTEIRO", "LITERAL_REAL", "LITERAL_STRING", "LITERAL_CHAR", "(", "!", "-"]
INICIO_INSTRUCAO = ["int", "float", "char", "void", "IDENTIFICADOR", "if", "while", "return", "{"]
_INICIOS_SEGUROS = {"int", "float", "char", "void", "if", "while", "return", "{"}


def _regra(tipo_no: str) -> str:
    return NOS[tipo_no][0]


R_DECL = _regra("DECLARACAO_VARIAVEL")
R_ATRIB = _regra("ATRIBUICAO")
R_IF = _regra("CONDICIONAL")
R_WHILE = _regra("REPETICAO")
R_RETORNO = _regra("RETORNO")
R_BLOCO = _regra("BLOCO")
R_FUNC = _regra("DEFINICAO_FUNCAO")
R_PARAM = _regra("PARAMETRO")
R_CHAMADA = _regra("CHAMADA_FUNCAO")
R_PRIMARIO = _regra("IDENTIFICADOR")
R_UNARIO = _regra("NEGACAO_LOGICA")
R_PROGRAMA = _regra("PROGRAMA")


class ErroSintatico(Exception):
    """Erro de sintaxe interno; carrega o dicionário já no formato da API."""

    def __init__(self, dados: dict, idx: int = -1):
        super().__init__(dados["mensagem"])
        self.dados = dados
        self.idx = idx  # índice do token que causou o erro


def _foi_encontrado(tk: dict) -> str:
    """'foi encontrado o identificador x' / 'foi encontrada a palavra reservada while' (concordância)."""
    feminino = tk["tipo"] in ("PALAVRA_RESERVADA", "LITERAL_STRING")
    return f"foi {'encontrada' if feminino else 'encontrado'} {_descrever(tk)}"


def _descrever(tk: dict) -> str:
    """Descrição amigável de um token para as mensagens."""
    t, lex = tk["tipo"], tk["lexema"]
    if t == "FIM":
        return "o fim do código"
    if t == "IDENTIFICADOR":
        return f"o identificador '{lex}'"
    if t in ("LITERAL_INTEIRO", "LITERAL_REAL"):
        return f"o número {lex}"
    if t == "LITERAL_STRING":
        return f"a string {lex}"
    if t == "LITERAL_CHAR":
        return f"o caractere {lex}"
    if t == "PALAVRA_RESERVADA":
        return f"a palavra reservada '{lex}'"
    return f"'{lex}'"


class _Parser:
    def __init__(self, tokens: List[dict], codigo: str):
        self.u16 = codigo.encode("utf-16-le", "surrogatepass")
        self.eof = self._criar_eof(codigo)
        self.t = list(tokens) + [self.eof]
        self.i = 0
        self.erros: List[dict] = []
        self.blocos: List[dict] = []  # tokens '{' ainda abertos
        self.prof = 0
        self.parar = False
        self.truncado = False
        self.eof_reportado = False
        self.ultimo_erro_em_if: Optional[int] = None  # nível de bloco onde um if falhou (evita else órfão em cascata)

    # ------------------------------------------------------------------ utilidades
    @staticmethod
    def _posicao_final(codigo: str):
        linha, col, i, n = 1, 1, 0, len(codigo)
        while i < n:
            ch = codigo[i]
            if ch == "\r" and i + 1 < n and codigo[i + 1] == "\n":
                i += 2
                linha, col = linha + 1, 1
            elif ch in "\r\n":
                i += 1
                linha, col = linha + 1, 1
            else:
                i += 1
                col += 1
        return linha, col

    def _criar_eof(self, codigo: str) -> dict:
        linha, col = self._posicao_final(codigo)
        off = len(self.u16) // 2
        return {"tipo": "FIM", "lexema": "", "linha": linha, "coluna": col, "fim_linha": linha,
                "fim_coluna": col, "inicio": off, "fim": off, "caminho": []}

    def _fatia(self, ini: int, fim: int) -> str:
        return self.u16[ini * 2:fim * 2].decode("utf-16-le", "surrogatepass")

    def atual(self) -> dict:
        return self.t[self.i]

    def olhar(self, k: int) -> dict:
        return self.t[min(self.i + k, len(self.t) - 1)]

    def avancar(self) -> int:
        i = self.i
        if self.t[i]["tipo"] != "FIM":
            self.i += 1
        return i

    def eh(self, *lexemas, tk: Optional[dict] = None) -> bool:
        tk = tk or self.atual()
        return tk["tipo"] != "FIM" and tk["lexema"] in lexemas

    def eh_ident(self, tk: Optional[dict] = None) -> bool:
        return (tk or self.atual())["tipo"] == "IDENTIFICADOR"

    # ------------------------------------------------------------------ nós da AST
    def _no(self, tipo, a, b, atributos=None, filhos=None):
        ta, tb = self.t[a], self.t[b]
        return {
            "tipo": tipo, "id": 0, "papel": None,
            "linha": ta["linha"], "coluna": ta["coluna"],
            "fim_linha": tb["fim_linha"], "fim_coluna": tb["fim_coluna"],
            "inicio": ta["inicio"], "fim": tb["fim"],
            "atributos": atributos or {}, "filhos": filhos or [],
            "_a": a, "_b": b,
        }

    @staticmethod
    def _papel(no: dict, papel: str) -> dict:
        no["papel"] = papel
        return no

    def _reposicionar(self, no: dict, a: int, b: int) -> None:
        ta, tb = self.t[a], self.t[b]
        no.update({"linha": ta["linha"], "coluna": ta["coluna"], "fim_linha": tb["fim_linha"],
                   "fim_coluna": tb["fim_coluna"], "inicio": ta["inicio"], "fim": tb["fim"],
                   "_a": a, "_b": b})

    # ------------------------------------------------------------------ erros
    def _indice(self, tk: dict) -> int:
        for k in range(max(0, self.i - 3), min(len(self.t), self.i + 4)):
            if self.t[k] is tk:
                return k
        return -1

    def _erro(self, tk, esperado, mensagem, regra=None, dica=None) -> ErroSintatico:
        return ErroSintatico({
            "tipo": "ERRO_SINTATICO",
            "linha": tk["linha"], "coluna": tk["coluna"], "inicio": tk["inicio"], "fim": tk["fim"],
            "encontrado": "fim do código" if tk["tipo"] == "FIM" else tk["lexema"],
            "encontrado_tipo": tk["tipo"],
            "esperado": esperado,
            "mensagem": mensagem,
            "regra": regra,
            "dica": dica,
        }, self._indice(tk))

    def _esperado(self, tk, esperado, base, regra=None, dica=None) -> ErroSintatico:
        if tk["tipo"] == "FIM":
            msg = f"{base}, mas o código terminou antes disso."
        else:
            msg = f"{base}, mas {_foi_encontrado(tk)}."
        return self._erro(tk, esperado, msg, regra, dica)

    def esperar(self, lex: str, onde: str, regra=None, dica=None) -> int:
        tk = self.atual()
        if self.eh(lex):
            return self.avancar()
        if lex == ";" and dica is None and self.i > 0 and tk["tipo"] != "FIM" \
                and self.t[self.i - 1]["fim_linha"] < tk["linha"]:
            dica = "Confira se faltou ';' no fim da linha anterior."
        if dica is None and self.eh("[", "]", tk=tk):
            dica = "Os colchetes não fazem parte da gramática deste subconjunto (arrays não são suportados)."
        raise self._esperado(tk, [lex], f"Era esperado '{lex}' {onde}", regra, dica)

    def esperar_identificador(self, onde: str, regra=None) -> int:
        tk = self.atual()
        if self.eh_ident(tk):
            return self.avancar()
        if tk["tipo"] == "PALAVRA_RESERVADA":
            raise self._erro(
                tk, ["IDENTIFICADOR"],
                f"Era esperado um nome (identificador) {onde}, mas '{tk['lexema']}' é uma palavra "
                "reservada e não pode ser usada como nome.", regra,
                "Escolha outro nome: palavras reservadas têm significado fixo na linguagem.")
        raise self._esperado(tk, ["IDENTIFICADOR"], f"Era esperado um nome (identificador) {onde}", regra)

    def entrar(self) -> None:
        if self.prof >= LIMITE_ANINHAMENTO:  # verifica antes de incrementar: o contador não "vaza" ao lançar
            raise self._erro(
                self.atual(), [],
                f"O código tem aninhamento profundo demais (mais de {LIMITE_ANINHAMENTO} níveis "
                "de parênteses, blocos ou operadores unários).", None,
                "Simplifique a estrutura ou divida o programa em partes menores.")
        self.prof += 1

    def sair(self) -> None:
        self.prof -= 1

    def _fim_de_item(self, no: dict) -> None:
        """Um comando comum concluído no mesmo nível encerra o contexto de 'if com erro'."""
        if no["tipo"] != "BLOCO" and self.ultimo_erro_em_if == len(self.blocos):
            self.ultimo_erro_em_if = None

    def registrar(self, e: ErroSintatico) -> None:
        if self.parar:
            return
        d = e.dados
        if d["encontrado_tipo"] == "FIM":
            if self.eof_reportado:
                return
            self.eof_reportado = True
        if self.erros and self.erros[-1]["inicio"] == d["inicio"] and self.erros[-1]["mensagem"] == d["mensagem"]:
            return
        self.erros.append(d)
        if len(self.erros) >= LIMITE_ERROS:
            self.parar = True
            self.truncado = True

    def sincronizar(self, dentro_de_bloco: bool, e: Optional[ErroSintatico] = None) -> None:
        """Modo pânico: descarta tokens até um ponto seguro para recomeçar."""
        if e is not None:
            esperado = e.dados["esperado"]
            if esperado == [";"] and self.eh_ident():
                return  # provável ';' esquecido no fim da linha anterior: não descarte a próxima instrução
            tk = self.atual()
            if (esperado != [";"] and e.idx == self.i and tk["tipo"] == "PALAVRA_RESERVADA"
                    and tk["lexema"] in _INICIOS_SEGUROS):
                self.avancar()  # a palavra reservada ofensora não deve reiniciar a análise (evita cascata)
        while self.atual()["tipo"] != "FIM":
            tk = self.atual()
            if self.eh(";"):
                self.avancar()
                return
            if self.eh("}"):
                if not dentro_de_bloco:
                    self.avancar()
                return
            if tk["lexema"] in _INICIOS_SEGUROS and tk["tipo"] in ("PALAVRA_RESERVADA", "DELIMITADOR"):
                return
            self.avancar()

    # ------------------------------------------------------------------ programa e itens
    def executar(self) -> Optional[dict]:
        itens: List[dict] = []
        while self.atual()["tipo"] != "FIM" and not self.parar:
            ini = self.i
            try:
                no = self.item("global")
                itens.append(self._papel(no, "item"))
                self._fim_de_item(no)
            except ErroSintatico as e:
                self.prof = 0
                self.blocos = []
                self.registrar(e)
                self.sincronizar(False, e)
                if self.i == ini and self.atual()["tipo"] != "FIM":
                    self.i += 1
        if self.erros:
            return None
        n_tokens = len(self.t) - 1
        if n_tokens == 0:
            programa = self._no("PROGRAMA", 0, 0, filhos=itens)
            programa.update({"linha": 1, "coluna": 1, "inicio": 0})
        else:
            programa = self._no("PROGRAMA", 0, n_tokens - 1, filhos=itens)
        return programa

    def item(self, ctx: str) -> dict:
        """Item de programa ('global') ou de bloco ('bloco'): função, declaração ou comando."""
        tk = self.atual()
        if tk["tipo"] == "PALAVRA_RESERVADA" and tk["lexema"] in TIPOS_RETORNO:
            eh_funcao = tk["lexema"] == "void" or (self.eh_ident(self.olhar(1)) and self.eh("(", tk=self.olhar(2)))
            if eh_funcao:
                if ctx != "global":
                    raise self._erro(
                        tk, [],
                        "Funções só podem ser definidas fora de blocos: não é permitido definir uma função "
                        "dentro de outra construção.", R_FUNC,
                        "Mova a definição da função para fora das chaves.")
                return self.definicao_funcao()
            return self.declaracao()
        return self.comando(ctx)

    # ------------------------------------------------------------------ declarações e funções
    def declaracao(self) -> dict:
        a = self.avancar()
        tipo = self.t[a]["lexema"]
        n = self.esperar_identificador(f"depois do tipo '{tipo}'", R_DECL)
        nome = self._fatia(self.t[n]["inicio"], self.t[n]["fim"])
        filhos = []
        if self.eh("="):
            self.avancar()
            filhos.append(self._papel(self.expressao(f"depois de '=' na declaração de '{nome}'"), "valor"))
        fim = self.esperar(";", "ao final da declaração", R_DECL)
        return self._no("DECLARACAO_VARIAVEL", a, fim, {"tipo_dado": tipo, "nome": nome}, filhos)

    def definicao_funcao(self) -> dict:
        a = self.avancar()
        tipo = self.t[a]["lexema"]
        n = self.esperar_identificador(f"depois do tipo de retorno '{tipo}'", R_FUNC)
        nome = self._fatia(self.t[n]["inicio"], self.t[n]["fim"])
        if tipo == "void" and not self.eh("("):
            raise self._erro(
                self.atual(), ["("],
                f"'void' só pode ser usado como tipo de retorno de função, não como tipo da variável '{nome}'.",
                R_FUNC, "Use int, float ou char para variáveis.")
        self.esperar("(", f"depois do nome da função '{nome}'", R_FUNC)
        params: List[dict] = []
        if not self.eh(")"):
            while True:
                params.append(self._papel(self.parametro(), "parametro"))
                if self.eh(","):
                    self.avancar()
                    continue
                break
        if not self.eh(")"):
            raise self._esperado(self.atual(), [",", ")"],
                                 f"Era esperado ',' ou ')' na lista de parâmetros da função '{nome}'", R_PARAM)
        self.avancar()
        if not self.eh("{"):
            raise self._esperado(
                self.atual(), ["{"], f"Era esperado '{{' para iniciar o corpo da função '{nome}'", R_FUNC,
                "Protótipos de função (declaração sem corpo) não fazem parte do subconjunto.")
        corpo = self._papel(self.bloco(), "corpo")
        return self._no("DEFINICAO_FUNCAO", a, self.i - 1, {"tipo_retorno": tipo, "nome": nome}, params + [corpo])

    def parametro(self) -> dict:
        tk = self.atual()
        if not (tk["tipo"] == "PALAVRA_RESERVADA" and tk["lexema"] in TIPOS_DADO):
            if self.eh("void"):
                raise self._erro(tk, list(TIPOS_DADO),
                                 "'void' não pode ser tipo de parâmetro neste subconjunto.", R_PARAM,
                                 "Para uma função sem parâmetros, deixe os parênteses vazios: f().")
            raise self._esperado(tk, list(TIPOS_DADO), "Era esperado o tipo do parâmetro (int, float ou char)",
                                 R_PARAM)
        a = self.avancar()
        n = self.esperar_identificador(f"depois do tipo '{tk['lexema']}' do parâmetro", R_PARAM)
        nome = self._fatia(self.t[n]["inicio"], self.t[n]["fim"])
        return self._no("PARAMETRO", a, n, {"tipo_dado": tk["lexema"], "nome": nome})

    # ------------------------------------------------------------------ comandos
    def comando(self, ctx: str) -> dict:
        tk = self.atual()
        lx, tp = tk["lexema"], tk["tipo"]
        if tp == "PALAVRA_RESERVADA":
            if lx == "if":
                return self.condicional()
            if lx == "while":
                return self.repeticao()
            if lx == "return":
                return self.retorno()
            if lx == "else":
                if self.ultimo_erro_em_if == len(self.blocos):  # else órfão por causa de um erro no if: não repita o problema
                    self.avancar()
                    self.ultimo_erro_em_if = None
                    return self.corpo()
                raise self._erro(
                    tk, [],
                    "'else' sem 'if' correspondente: um else precisa vir logo depois do comando ou bloco de um if.",
                    R_IF, "Confira se o if anterior está completo e se não há um ';' ou '}' sobrando antes do else.")
            if lx in TIPOS_RETORNO:  # só chega aqui quando a declaração não é permitida (corpo de if/while)
                raise self._erro(
                    tk, ["{"],
                    "Declarações de variável precisam estar dentro de um bloco { } quando aparecem no corpo "
                    "de um if ou while.", R_BLOCO,
                    "Coloque o corpo entre chaves: if (...) { int x = 1; }")
        if tp == "DELIMITADOR" and lx == "{":
            return self.bloco()
        if tp == "IDENTIFICADOR":
            prox = self.olhar(1)
            if self.eh("=", tk=prox):
                return self.atribuicao()
            if self.eh("(", tk=prox):
                chamada = self.chamada()
                self.esperar(";", "ao final da chamada de função", R_CHAMADA)
                return chamada
            raise self._esperado(
                prox, ["=", "("],
                f"Depois do nome '{lx}' era esperado '=' (atribuição) ou '(' (chamada de função)", R_ATRIB)
        raise self._erro_inicio_instrucao(tk, ctx)

    def _erro_inicio_instrucao(self, tk: dict, ctx: str) -> ErroSintatico:
        esperado = list(INICIO_INSTRUCAO if ctx != "corpo" else INICIO_INSTRUCAO[4:])
        lx = tk["lexema"]
        if lx == "}":
            return self._erro(tk, esperado, "'}' sem '{' correspondente: não há bloco aberto para fechar.",
                              R_BLOCO, "Remova o '}' sobrando ou confira se faltou um '{' antes.")
        if lx == ")":
            return self._erro(tk, esperado, "')' sem '(' correspondente: não há parêntese aberto para fechar.",
                              R_PRIMARIO, "Remova o ')' sobrando ou confira se faltou um '(' antes.")
        if lx == ";":
            return self._erro(tk, esperado, "Foi encontrado ';' sozinho onde se esperava uma instrução: "
                              "instruções vazias não fazem parte do subconjunto.", None,
                              "Remova o ';' extra (se estiver depois de um if ou while, ele encerra o comando antes do corpo).")
        if lx in ("[", "]"):
            return self._erro(tk, esperado, f"Os colchetes ('{lx}') são reconhecidos pelo scanner, mas não fazem "
                              "parte da gramática deste subconjunto.", None, "Arrays não são suportados.")
        return self._erro(
            tk, esperado,
            f"Uma instrução não pode começar com {_descrever(tk)}. Uma instrução começa com um tipo "
            "(int, float, char, void), um nome (atribuição ou chamada), if, while, return ou '{'.", None,
            "Expressões soltas (como 10; ou a + b;) não são instruções neste subconjunto.")

    def atribuicao(self) -> dict:
        a = self.avancar()
        nome = self._fatia(self.t[a]["inicio"], self.t[a]["fim"])
        self.avancar()  # '='
        valor = self._papel(self.expressao(f"depois de '=' na atribuição a '{nome}'"), "valor")
        fim = self.esperar(";", "ao final da atribuição", R_ATRIB)
        return self._no("ATRIBUICAO", a, fim, {"nome": nome}, [valor])

    def corpo(self) -> dict:
        self.entrar()
        try:
            return self.comando("corpo")
        finally:
            self.sair()

    def _condicao(self, palavra: str, regra: str):
        self.esperar("(", f"depois de '{palavra}' (a condição vem entre parênteses)", regra)
        cond = self._papel(self.expressao(f"na condição do {palavra}"), "condicao")
        self.esperar(")", f"para fechar a condição do {palavra}", regra)
        return cond

    def condicional(self) -> dict:
        a = self.avancar()
        try:
            cond = self._condicao("if", R_IF)
            filhos = [cond, self._papel(self.corpo(), "entao")]
            if self.eh("else"):
                self.avancar()
                filhos.append(self._papel(self.corpo(), "senao"))
        except ErroSintatico:
            self.ultimo_erro_em_if = len(self.blocos)
            raise
        return self._no("CONDICIONAL", a, self.i - 1, {"tem_senao": len(filhos) == 3}, filhos)

    def repeticao(self) -> dict:
        a = self.avancar()
        cond = self._condicao("while", R_WHILE)
        corpo = self._papel(self.corpo(), "corpo")
        return self._no("REPETICAO", a, self.i - 1, {}, [cond, corpo])

    def retorno(self) -> dict:
        a = self.avancar()
        filhos = []
        if not self.eh(";"):
            filhos.append(self._papel(self.expressao("depois de 'return'"), "valor"))
        fim = self.esperar(";", "ao final do return", R_RETORNO,
                           "Se a função não devolve valor, escreva apenas 'return;'.")
        return self._no("RETORNO", a, fim, {}, filhos)

    def bloco(self) -> dict:
        a = self.i
        abre = self.t[a]
        self.avancar()
        self.entrar()
        self.blocos.append(abre)
        try:
            filhos: List[dict] = []
            while not self.eh("}"):
                if self.atual()["tipo"] == "FIM" or self.parar:
                    if self.parar:
                        break
                    raise self._erro_bloco_aberto()
                ini = self.i
                try:
                    no = self.item("bloco")
                    filhos.append(self._papel(no, "instrucao"))
                    self._fim_de_item(no)
                except ErroSintatico as e:
                    if e.dados["encontrado_tipo"] == "FIM" and self.eof_reportado:
                        raise
                    self.registrar(e)
                    self.sincronizar(True, e)
                    if self.i == ini and self.atual()["tipo"] != "FIM" and not self.eh("}"):
                        self.i += 1
            fim = self.i if self.eh("}") else self.i - 1
            if self.eh("}"):
                self.avancar()
            return self._no("BLOCO", a, fim, {}, filhos)
        finally:
            self.blocos.pop()
            self.sair()

    def _erro_bloco_aberto(self) -> ErroSintatico:
        abertos = self.blocos
        if len(abertos) == 1:
            msg = f"O código terminou antes de o bloco aberto na linha {abertos[0]['linha']} ser fechado com '}}'."
        else:
            linhas = ", ".join(str(t["linha"]) for t in abertos)
            msg = (f"O código terminou antes de {len(abertos)} blocos abertos serem fechados com '}}' "
                   f"(abertos nas linhas {linhas}).")
        return self._erro(self.eof, ["}"], msg, R_BLOCO, "Para cada '{' deve existir um '}' correspondente.")

    # ------------------------------------------------------------------ expressões
    def expressao(self, ctx: str) -> dict:
        return self.binaria(0, ctx)

    def binaria(self, nivel: int, ctx: str) -> dict:
        if nivel == len(NIVEIS):
            return self.unario(ctx)
        esq = self.binaria(nivel + 1, ctx)
        while self.atual()["tipo"].startswith("OPERADOR") and self.atual()["lexema"] in NIVEIS[nivel]:
            op = self.t[self.avancar()]["lexema"]
            dir_ = self.binaria(nivel + 1, f"depois do operador '{op}'")
            if op in TIPO_ARITMETICO:
                tipo = TIPO_ARITMETICO[op]
            elif op in ("&&", "||"):
                tipo = "OPERACAO_LOGICA"
            else:
                tipo = "COMPARACAO"
            no = self._no(tipo, esq["_a"], dir_["_b"], {"operador": op},
                          [self._papel(esq, "esquerda"), self._papel(dir_, "direita")])
            esq = no
        return esq

    def unario(self, ctx: str) -> dict:
        tk = self.atual()
        if tk["tipo"].startswith("OPERADOR") and tk["lexema"] in ("!", "-"):
            a = self.avancar()
            self.entrar()
            try:
                operando = self._papel(self.unario(f"depois do operador '{tk['lexema']}'"), "operando")
            finally:
                self.sair()
            tipo = "NEGACAO_LOGICA" if tk["lexema"] == "!" else "MENOS_UNARIO"
            return self._no(tipo, a, operando["_b"], {"operador": tk["lexema"]}, [operando])
        return self.primario(ctx)

    def primario(self, ctx: str) -> dict:
        tk = self.atual()
        tp = tk["tipo"]
        if tp == "IDENTIFICADOR":
            if self.eh("(", tk=self.olhar(1)):
                return self.chamada()
            a = self.avancar()
            return self._no("IDENTIFICADOR", a, a, {"nome": self._fatia(tk["inicio"], tk["fim"])})
        if tp in LITERAIS:
            a = self.avancar()
            return self._no(tp, a, a, {"valor": self._fatia(tk["inicio"], tk["fim"])})
        if self.eh("("):
            abre = self.avancar()
            self.entrar()
            try:
                e = self.expressao("dentro dos parênteses")
                fecha = self.esperar(
                    ")", f"para fechar o '(' aberto na linha {tk['linha']}, coluna {tk['coluna']}", R_PRIMARIO)
            finally:
                self.sair()
            self._reposicionar(e, abre, fecha)  # o trecho do nó inclui os parênteses; eles não viram nós
            return e
        raise self._erro_operando(tk, ctx)

    def _erro_operando(self, tk: dict, ctx: str) -> ErroSintatico:
        if tk["tipo"] == "FIM":
            return self._erro(
                tk, list(INICIO_EXPRESSAO), f"Era esperada uma expressão {ctx}, mas o código terminou antes disso.",
                R_PRIMARIO, "Complete a expressão com um número, uma variável, uma chamada ou uma expressão entre parênteses.")
        if tk["tipo"].startswith("OPERADOR") and ctx.startswith("depois do operador") and tk["lexema"] not in ("!", "-"):
            return self._erro(
                tk, list(INICIO_EXPRESSAO),
                f"Operadores consecutivos: {ctx} era esperado um operando (número, variável, chamada ou "
                f"expressão entre parênteses), mas {_foi_encontrado(tk)}.", R_PRIMARIO,
                "Cada operador binário precisa de um operando de cada lado.")
        if tk["tipo"] == "PALAVRA_RESERVADA":
            return self._erro(
                tk, list(INICIO_EXPRESSAO),
                f"Era esperada uma expressão {ctx}, mas {_descrever(tk)} é uma palavra reservada e não pode "
                "ser usada como valor.", R_PRIMARIO, None)
        return self._erro(
            tk, list(INICIO_EXPRESSAO),
            f"Era esperada uma expressão {ctx}, mas {_foi_encontrado(tk)}.", R_PRIMARIO,
            "Uma expressão é um número, uma variável, uma chamada de função ou uma expressão entre parênteses.")

    def chamada(self) -> dict:
        a = self.avancar()
        nome = self._fatia(self.t[a]["inicio"], self.t[a]["fim"])
        self.avancar()  # '('
        args: List[dict] = []
        if not self.eh(")"):
            while True:
                args.append(self._papel(self.expressao(f"no argumento da chamada de '{nome}'"), "argumento"))
                if self.eh(","):
                    self.avancar()
                    continue
                break
        if not self.eh(")"):
            raise self._esperado(self.atual(), [",", ")"],
                                 f"Era esperado ',' ou ')' na lista de argumentos da chamada de '{nome}'", R_CHAMADA)
        fim = self.avancar()
        return self._no("CHAMADA_FUNCAO", a, fim, {"nome": nome}, args)


# ====================================================================== pós-processamento
def _rotulo(no: dict) -> str:
    attrs = " ".join(f"{k}={v}" for k, v in no["atributos"].items())
    papel = f"{no['papel']}: " if no["papel"] else ""
    return f"{papel}{no['tipo']}" + (f" ({attrs})" if attrs else "") + f"  [{no['linha']}:{no['coluna']}]"


def texto_arvore(ast: dict) -> str:
    """Versão em texto indentado da AST (acessível a leitores de tela)."""
    linhas = [_rotulo(ast)]

    def rec(no, prefixo):
        n = len(no["filhos"])
        for k, f in enumerate(no["filhos"]):
            ultimo = k == n - 1
            linhas.append(prefixo + ("└── " if ultimo else "├── ") + _rotulo(f))
            rec(f, prefixo + ("    " if ultimo else "│   "))

    rec(ast, "")
    return "\n".join(linhas)


def _finalizar(ast: dict):
    """Numera os nós em pré-ordem, remove campos internos e calcula estatísticas (sem recursão)."""
    total, altura, por_tipo = 0, 0, {}
    pilha = [(ast, 1)]
    while pilha:
        no, nivel = pilha.pop()
        total += 1
        no["id"] = total
        no.pop("_a", None)
        no.pop("_b", None)
        altura = max(altura, nivel)
        por_tipo[no["tipo"]] = por_tipo.get(no["tipo"], 0) + 1
        pilha.extend((f, nivel + 1) for f in reversed(no["filhos"]))
    return {"total_nos": total, "altura": altura, "por_tipo": por_tipo}


def _plural(n: int, s: str, p: str) -> str:
    return f"{n} {s if n == 1 else p}"


def analisar_sintaxe(tokens: List[dict], codigo: str) -> Dict:
    """Executa a análise sintática sobre os tokens do scanner. Nunca levanta exceção."""
    parser = _Parser(tokens, codigo)
    ast = parser.executar()
    erros = parser.erros
    resumo, texto, regras = None, None, {}

    if ast is not None:
        resumo = _finalizar(ast)
        if resumo["altura"] > LIMITE_ALTURA:
            erros = [{
                "tipo": "ERRO_SINTATICO", "linha": ast["linha"], "coluna": ast["coluna"],
                "inicio": ast["inicio"], "fim": ast["fim"], "encontrado": "", "encontrado_tipo": "LIMITE",
                "esperado": [],
                "mensagem": f"A árvore sintática ficou profunda demais (mais de {LIMITE_ALTURA} níveis).",
                "regra": None,
                "dica": "Divida expressões muito longas em várias instruções.",
            }]
            ast, resumo = None, None
        else:
            regras = regras_dos_tipos(resumo["por_tipo"].keys())
            if resumo["total_nos"] <= LIMITE_NOS_TEXTO:
                texto = texto_arvore(ast)

    if ast is not None:
        n = resumo["total_nos"]
        vazio = not tokens
        mensagem = (f"Análise sintática concluída: {'programa vazio' if vazio else 'programa válido'} "
                    f"(AST com {_plural(n, 'nó', 'nós')}).")
    else:
        mensagem = (f"Análise sintática concluída com {_plural(len(erros), 'erro sintático', 'erros sintáticos')}"
                    f"{' (limite de ' + str(LIMITE_ERROS) + ' erros atingido)' if parser.truncado else ''}; "
                    "a AST não foi construída.")
    return {
        "executado": True,
        "sucesso": ast is not None,
        "mensagem": mensagem,
        "motivo": None,
        "ast": ast,
        "erros": erros,
        "erros_truncados": parser.truncado,
        "resumo": resumo,
        "regras": regras,
        "texto": texto,
    }


def nao_executado(motivo: str) -> Dict:
    """Resultado sintático quando o parser não roda (erros léxicos)."""
    return {
        "executado": False,
        "sucesso": None,
        "mensagem": "A análise sintática não foi executada.",
        "motivo": motivo,
        "ast": None,
        "erros": [],
        "erros_truncados": False,
        "resumo": None,
        "regras": {},
        "texto": None,
    }
