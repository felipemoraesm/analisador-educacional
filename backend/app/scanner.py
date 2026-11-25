"""Analisador léxico (scanner) do subconjunto de C.

O scanner lê o código caractere a caractere, agrupa os caracteres em lexemas
(sempre pelo *maior casamento possível*) e classifica cada lexema em uma
categoria de token. Espaços em branco e comentários são descartados. Caracteres
ou sequências inválidas geram erros léxicos com posição, e a leitura continua
logo depois deles, de modo que todos os problemas aparecem de uma só vez.

Para fins didáticos, cada token e cada erro traz o ``caminho`` percorrido pelo
autômato: uma lista com, para cada caractere consumido, a classe do caractere e
o estado em que o autômato ficou.

Convenções de posição
- ``linha`` e ``coluna`` começam em 1 e contam caracteres (um tab conta 1).
- Tokens também trazem ``fim_linha`` e ``fim_coluna`` (posição logo após o último
  caractere), usados pelo parser para registrar o trecho de cada nó da AST.
- ``inicio`` e ``fim`` são deslocamentos (início inclusivo, fim exclusivo) em
  unidades UTF-16, para o frontend poder fatiar a string do JavaScript
  diretamente, mesmo com emojis.

Este módulo não valida a estrutura do programa (isso é papel do parser).
"""

import re
from typing import Callable, Dict, List

PALAVRAS_RESERVADAS = ("int", "float", "char", "void", "if", "else", "while", "return")

# Categorias de token, na ordem em que aparecem nos resumos.
CATEGORIAS = (
    "PALAVRA_RESERVADA",
    "IDENTIFICADOR",
    "LITERAL_INTEIRO",
    "LITERAL_REAL",
    "LITERAL_STRING",
    "LITERAL_CHAR",
    "OPERADOR_ARITMETICO",
    "OPERADOR_RELACIONAL",
    "OPERADOR_LOGICO",
    "OPERADOR_ATRIBUICAO",
    "DELIMITADOR",
)

ERRO_LEXICO = "ERRO_LEXICO"

_DIGITOS = "0123456789"
_NOVA_LINHA = "\r\n"
_BRANCOS = " \t\f\v"
_ESCAPES_VALIDOS = "ntr0\\\"'"
_ARITMETICOS = "+-*%"
_DELIMITADORES = "(){}[];,"
_MAX_LEXEMA_EXIBIDO = 40

# Operadores de dois caracteres: lexema -> (tipo, estado do 1º char, estado do 2º char)
_OPS_DOIS = {
    "==": ("OPERADOR_RELACIONAL", "IGUAL", "IGUAL_IGUAL"),
    "!=": ("OPERADOR_RELACIONAL", "EXCLAMACAO", "DIFERENTE"),
    "<=": ("OPERADOR_RELACIONAL", "MENOR", "MENOR_IGUAL"),
    ">=": ("OPERADOR_RELACIONAL", "MAIOR", "MAIOR_IGUAL"),
    "&&": ("OPERADOR_LOGICO", "E_COMERCIAL", "E_LOGICO"),
    "||": ("OPERADOR_LOGICO", "BARRA_VERTICAL", "OU_LOGICO"),
}
# Operadores de um caractere formados por prefixos de operadores de dois: lexema -> (tipo, estado)
_OPS_UM_PREFIXO = {
    "=": ("OPERADOR_ATRIBUICAO", "IGUAL"),
    "!": ("OPERADOR_LOGICO", "EXCLAMACAO"),
    "<": ("OPERADOR_RELACIONAL", "MENOR"),
    ">": ("OPERADOR_RELACIONAL", "MAIOR"),
}

_DICAS_CARACTERE = {
    "#": "Diretivas do pré-processador (como #include) não fazem parte do subconjunto.",
    ".": (
        "O ponto só é aceito dentro de números reais, como 3.14. "
        "Para um valor menor que 1, escreva 0.5 em vez de .5."
    ),
}
_DICA_PADRAO = "Verifique se ele faz parte do subconjunto suportado."


def _eh_letra(c: str) -> bool:
    """Letra ASCII ou sublinhado (início de identificador)."""
    return c == "_" or ("a" <= c <= "z") or ("A" <= c <= "Z")


def _eh_digito(c: str) -> bool:
    return c in _DIGITOS and c != ""


def _classe(c: str) -> str:
    if c == "_":
        return "sublinhado"
    if _eh_letra(c):
        return "letra"
    if _eh_digito(c):
        return "digito"
    if c == ".":
        return "ponto"
    if c == '"':
        return "aspas"
    if c == "'":
        return "apostrofo"
    if c == "\\":
        return "barra_invertida"
    return "simbolo"


def _mostrar(c: str) -> str:
    """Representação segura de um caractere para mensagens."""
    if c.isprintable() and not c.isspace():
        return c
    return f"U+{ord(c):04X}"


def _exibir(lexema: str) -> str:
    if len(lexema) > _MAX_LEXEMA_EXIBIDO:
        return lexema[: _MAX_LEXEMA_EXIBIDO - 1] + "…"
    return lexema


def _passo(c: str, estado: str) -> Dict[str, str]:
    return {"c": c, "classe": _classe(c), "estado": estado}


def _afd_numero(corrida: str) -> List[Dict[str, str]]:
    """Simula o autômato de números sobre a corrida de caracteres [A-Za-z0-9_.]."""
    estado = "INICIO"
    caminho = []
    for c in corrida:
        if estado == "INICIO":
            estado = "INT" if _eh_digito(c) else "ERRO"
        elif estado == "INT":
            estado = "INT" if _eh_digito(c) else ("REAL_PONTO" if c == "." else "ERRO")
        elif estado == "REAL_PONTO":
            estado = "REAL" if _eh_digito(c) else "ERRO"
        elif estado == "REAL":
            estado = "REAL" if _eh_digito(c) else "ERRO"
        # ERRO é absorvente
        caminho.append(_passo(c, estado))
    return caminho


def _mensagem_numero(corrida: str):
    """Mensagem e dica para um literal numérico malformado."""
    if re.match(r"0[xX]", corrida):
        return (
            f"Literal numérico não suportado '{corrida}': números hexadecimais não fazem parte do subconjunto.",
            "Use números decimais, como 31 em vez de 0x1F.",
        )
    if re.fullmatch(r"\d+(\.\d+)?[eE]\d*", corrida):
        return (
            f"Literal numérico não suportado '{corrida}': notação científica não faz parte do subconjunto.",
            "Escreva o número por extenso, como 100000.0.",
        )
    if re.fullmatch(r"\d+\.", corrida):
        return (
            f"Literal real malformado '{corrida}': faltam dígitos depois do ponto decimal.",
            "Escreva, por exemplo, 3.0 em vez de 3.",
        )
    if corrida.count(".") >= 2 and not re.search(r"[A-Za-z_]", corrida):
        return (
            f"Literal numérico malformado '{corrida}': um número real tem apenas um ponto decimal.",
            "Confira se não faltou um operador ou um separador entre os números.",
        )
    if re.match(r"\d+[A-Za-z_]", corrida):
        return (
            f"'{corrida}' não é válido: um identificador não pode começar com dígito.",
            "Se queria um identificador, comece com letra ou '_' (por exemplo, x2). "
            "Se queria um número, retire as letras.",
        )
    return (f"Literal numérico malformado '{corrida}'.", "Confira os dígitos e o ponto decimal.")


class _Scanner:
    def __init__(self, texto: str):
        self.t = texto
        self.n = len(texto)
        self.i = 0
        self.linha = 1
        self.col = 1
        self.tokens: List[dict] = []
        self.erros: List[dict] = []
        self.comentarios: List[dict] = []
        self._off: Callable[[int], int] = self._criar_offsets(texto)

    @staticmethod
    def _criar_offsets(texto: str) -> Callable[[int], int]:
        if not any(ord(ch) > 0xFFFF for ch in texto):
            return lambda k: k
        prefixo = [0]
        for ch in texto:
            prefixo.append(prefixo[-1] + (2 if ord(ch) > 0xFFFF else 1))
        return prefixo.__getitem__

    # ---------- controle de posição ----------
    def _avancar_ate(self, fim: int) -> None:
        t, j = self.t, self.i
        while j < fim:
            ch = t[j]
            if ch == "\r" and j + 1 < self.n and t[j + 1] == "\n":
                j += 2
                self.linha += 1
                self.col = 1
            elif ch in _NOVA_LINHA:
                j += 1
                self.linha += 1
                self.col = 1
            else:
                j += 1
                self.col += 1
        self.i = j

    # ---------- emissão ----------
    def _token(self, tipo, ini, fim, linha, col, caminho):
        self.tokens.append({
            "tipo": tipo,
            "lexema": _exibir(self.t[ini:fim]),
            "linha": linha,
            "coluna": col,
            "fim_linha": linha,  # nenhum token ocupa mais de uma linha
            "fim_coluna": col + (fim - ini),  # coluna logo após o último caractere (Etapa 4)
            "inicio": self._off(ini),
            "fim": self._off(fim),
            "caminho": caminho,
        })

    def _erro(self, ini, fim, linha, col, mensagem, dica, caminho=None):
        if caminho is None:
            caminho = [_passo(ch, "ERRO") for ch in self.t[ini:fim]]
        elif caminho:
            caminho = caminho[:-1] + [{**caminho[-1], "estado": "ERRO"}]
        self.erros.append({
            "tipo": ERRO_LEXICO,
            "lexema": _exibir(self.t[ini:fim]),
            "linha": linha,
            "coluna": col,
            "inicio": self._off(ini),
            "fim": self._off(fim),
            "mensagem": mensagem,
            "dica": dica,
            "caminho": caminho,
        })

    def _comentario(self, tipo, ini, fim, linha, col):
        self.comentarios.append({
            "tipo": tipo,
            "lexema": _exibir(self.t[ini:fim]),
            "linha": linha,
            "coluna": col,
            "inicio": self._off(ini),
            "fim": self._off(fim),
        })

    # ---------- laço principal ----------
    def executar(self) -> dict:
        t, n = self.t, self.n
        while self.i < n:
            c = t[self.i]
            if c in _BRANCOS or c in _NOVA_LINHA:
                fim = self.i + 2 if (c == "\r" and self.i + 1 < n and t[self.i + 1] == "\n") else self.i + 1
                self._avancar_ate(fim)
                continue

            ini, linha, col = self.i, self.linha, self.col
            if _eh_letra(c):
                fim = self._ident(ini, linha, col)
            elif _eh_digito(c):
                fim = self._numero(ini, linha, col)
            elif c == '"':
                fim = self._string(ini, linha, col)
            elif c == "'":
                fim = self._caractere(ini, linha, col)
            elif c == "/":
                fim = self._barra(ini, linha, col)
            elif c in "=!<>&|":
                fim = self._operador_composto(ini, linha, col)
            elif c in _ARITMETICOS:
                self._token("OPERADOR_ARITMETICO", ini, ini + 1, linha, col, [_passo(c, "OP_ARITMETICO")])
                fim = ini + 1
            elif c in _DELIMITADORES:
                self._token("DELIMITADOR", ini, ini + 1, linha, col, [_passo(c, "DELIMITADOR")])
                fim = ini + 1
            else:
                fim = self._desconhecido(ini, linha, col)
            self._avancar_ate(fim)
        return self._resultado()

    # ---------- reconhecedores (retornam o índice final do lexema) ----------
    def _ident(self, ini, linha, col):
        t, n, j = self.t, self.n, ini + 1
        while j < n and (_eh_letra(t[j]) or _eh_digito(t[j])):
            j += 1
        lexema = t[ini:j]
        tipo = "PALAVRA_RESERVADA" if lexema in PALAVRAS_RESERVADAS else "IDENTIFICADOR"
        self._token(tipo, ini, j, linha, col, [_passo(ch, "IDENT") for ch in lexema])
        return j

    def _numero(self, ini, linha, col):
        t, n, j = self.t, self.n, ini
        while j < n and (_eh_digito(t[j]) or _eh_letra(t[j]) or t[j] == "."):
            j += 1
        corrida = t[ini:j]
        caminho = _afd_numero(corrida)
        final = caminho[-1]["estado"]
        if final == "INT":
            self._token("LITERAL_INTEIRO", ini, j, linha, col, caminho)
        elif final == "REAL":
            self._token("LITERAL_REAL", ini, j, linha, col, caminho)
        else:
            mensagem, dica = _mensagem_numero(corrida)
            self._erro(ini, j, linha, col, mensagem, dica, caminho)
        return j

    def _string(self, ini, linha, col):
        t, n, j = self.t, self.n, ini + 1
        fechada, escape_invalido = False, None
        while j < n:
            ch = t[j]
            if ch == '"':
                fechada = True
                j += 1
                break
            if ch in _NOVA_LINHA:
                break
            if ch == "\\" and j + 1 < n and t[j + 1] not in _NOVA_LINHA:
                if t[j + 1] not in _ESCAPES_VALIDOS and escape_invalido is None:
                    escape_invalido = t[j:j + 2]
                j += 2
                continue
            j += 1
        lexema = t[ini:j]
        caminho = [_passo('"', "STRING")]
        em_escape = False
        for k, ch in enumerate(lexema[1:], start=1):
            if em_escape:
                estado, em_escape = "STRING", False
            elif ch == "\\":
                estado, em_escape = "STRING_ESC", True
            elif ch == '"' and fechada and k == len(lexema) - 1:
                estado = "STRING_FIM"
            else:
                estado = "STRING"
            caminho.append(_passo(ch, estado))
        if not fechada:
            self._erro(
                ini, j, linha, col,
                "String não fechada: faltou a aspa de fechamento (\") antes do fim da linha.",
                "Strings começam e terminam com aspas duplas na mesma linha.",
                caminho,
            )
        elif escape_invalido:
            self._erro(
                ini, j, linha, col,
                f"Sequência de escape inválida '{escape_invalido}' na string.",
                "Escapes aceitos: \\n, \\t, \\r, \\0, \\\\, \\\" e \\'.",
                caminho,
            )
        else:
            self._token("LITERAL_STRING", ini, j, linha, col, caminho)
        return j

    def _caractere(self, ini, linha, col):
        t, n, j = self.t, self.n, ini + 1
        fechado = False
        while j < n:
            ch = t[j]
            if ch == "'":
                fechado = True
                j += 1
                break
            if ch in _NOVA_LINHA:
                break
            if ch == "\\" and j + 1 < n and t[j + 1] not in _NOVA_LINHA:
                j += 2
                continue
            j += 1
        lexema = t[ini:j]
        caminho = [_passo("'", "CHAR_ABRE")]
        em_escape = False
        for k, ch in enumerate(lexema[1:], start=1):
            if em_escape:
                estado, em_escape = "CHAR_CONTEUDO", False
            elif ch == "\\":
                estado, em_escape = "CHAR_ESC", True
            elif ch == "'" and fechado and k == len(lexema) - 1:
                estado = "CHAR_FECHA"
            else:
                estado = "CHAR_CONTEUDO"
            caminho.append(_passo(ch, estado))

        if not fechado:
            self._erro(
                ini, j, linha, col,
                "Literal de caractere não fechado: faltou o apóstrofo (') de fechamento.",
                "Um caractere é escrito entre apóstrofos, como 'a'.",
                caminho,
            )
            return j
        conteudo = lexema[1:-1]
        if conteudo == "":
            self._erro(ini, j, linha, col, "Literal de caractere vazio ('').",
                       "Coloque exatamente um caractere entre os apóstrofos, como 'a'.", caminho)
        elif len(conteudo) == 1 and conteudo != "\\":
            self._token("LITERAL_CHAR", ini, j, linha, col, caminho)
        elif len(conteudo) == 2 and conteudo[0] == "\\" and conteudo[1] in _ESCAPES_VALIDOS:
            self._token("LITERAL_CHAR", ini, j, linha, col, caminho)
        elif len(conteudo) == 2 and conteudo[0] == "\\":
            self._erro(ini, j, linha, col, f"Sequência de escape inválida '{conteudo}' no caractere.",
                       "Escapes aceitos: \\n, \\t, \\r, \\0, \\\\, \\\" e \\'.", caminho)
        else:
            self._erro(ini, j, linha, col,
                       f"Literal de caractere com mais de um caractere: '{conteudo}'.",
                       "Um literal entre apóstrofos guarda um único caractere. "
                       "Para vários caracteres, use aspas duplas (string).", caminho)
        return j

    def _barra(self, ini, linha, col):
        t, n = self.t, self.n
        proximo = t[ini + 1] if ini + 1 < n else ""
        if proximo == "/":
            j = ini + 2
            while j < n and t[j] not in _NOVA_LINHA:
                j += 1
            self._comentario("COMENTARIO_LINHA", ini, j, linha, col)
            return j
        if proximo == "*":
            k = t.find("*/", ini + 2)
            if k == -1:
                self._erro(
                    ini, n, linha, col,
                    "Comentário de bloco não fechado: faltou o '*/'.",
                    "Todo o restante do código foi consumido como comentário. "
                    "Feche o comentário com */.",
                    caminho=[],
                )
                return n
            self._comentario("COMENTARIO_BLOCO", ini, k + 2, linha, col)
            return k + 2
        self._token("OPERADOR_ARITMETICO", ini, ini + 1, linha, col, [_passo("/", "BARRA")])
        return ini + 1

    def _operador_composto(self, ini, linha, col):
        t = self.t
        c = t[ini]
        par = t[ini:ini + 2]
        if par in _OPS_DOIS:
            tipo, e1, e2 = _OPS_DOIS[par]
            self._token(tipo, ini, ini + 2, linha, col, [_passo(par[0], e1), _passo(par[1], e2)])
            return ini + 2
        if c in _OPS_UM_PREFIXO:
            tipo, estado = _OPS_UM_PREFIXO[c]
            self._token(tipo, ini, ini + 1, linha, col, [_passo(c, estado)])
            return ini + 1
        # '&' ou '|' sozinhos
        if c == "&":
            dica = "O operador lógico E se escreve '&&'. O '&' sozinho (bit a bit/endereço) não faz parte do subconjunto."
        else:
            dica = "O operador lógico OU se escreve '||'. O '|' sozinho (bit a bit) não faz parte do subconjunto."
        self._erro(ini, ini + 1, linha, col, f"Caractere '{c}' sozinho não é reconhecido.", dica)
        return ini + 1

    def _desconhecido(self, ini, linha, col):
        c = self.t[ini]
        if c.isspace():
            self._erro(
                ini, ini + 1, linha, col,
                f"Caractere de espaço especial não reconhecido ({_mostrar(c)}).",
                "Apague-o e digite um espaço comum. Isso costuma acontecer ao colar texto de páginas da web.",
            )
        else:
            if c in _DICAS_CARACTERE:
                dica = _DICAS_CARACTERE[c]
            elif c.isalpha() and not c.isascii():
                dica = "Identificadores aceitam apenas letras sem acento (A-Z, a-z), dígitos e '_'."
            else:
                dica = _DICA_PADRAO
            self._erro(ini, ini + 1, linha, col, f"Caractere não reconhecido: '{_mostrar(c)}'", dica)
        return ini + 1

    # ---------- resultado ----------
    def _resultado(self) -> dict:
        por_categoria: Dict[str, int] = {}
        contagem = {}
        for tk in self.tokens:
            contagem[tk["tipo"]] = contagem.get(tk["tipo"], 0) + 1
        for cat in CATEGORIAS:
            if cat in contagem:
                por_categoria[cat] = contagem[cat]
        return {
            "sucesso": not self.erros,
            "tokens": self.tokens,
            "erros": self.erros,
            "comentarios": self.comentarios,
            "resumo": {
                "total_tokens": len(self.tokens),
                "total_erros": len(self.erros),
                "total_comentarios": len(self.comentarios),
                "por_categoria": por_categoria,
            },
        }


def tokenizar(codigo: str) -> dict:
    """Executa a análise léxica. Nunca levanta exceção para entradas de texto."""
    return _Scanner(codigo).executar()
