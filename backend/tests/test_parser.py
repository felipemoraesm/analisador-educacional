"""Testes unitários do parser (Etapa 4).

Os resultados esperados vêm da GRAMÁTICA (docs/gramatica.md), não do comportamento
atual do código: precedência, associatividade e mensagens são requisitos.
"""
import random
import time

import pytest

from app.parser import LIMITE_ALTURA, LIMITE_ANINHAMENTO, LIMITE_ERROS, analisar_sintaxe
from app.scanner import tokenizar

LITERAIS = {"LITERAL_INTEIRO", "LITERAL_REAL", "LITERAL_STRING", "LITERAL_CHAR"}


def analisar(codigo):
    lex = tokenizar(codigo)
    assert lex["sucesso"], f"o teste deve usar código sem erro léxico: {lex['erros']}"
    return analisar_sintaxe(lex["tokens"], codigo)


def ok(codigo):
    r = analisar(codigo)
    assert r["sucesso"] is True, [e["mensagem"] for e in r["erros"]]
    assert r["erros"] == []
    return r["ast"]


def erros(codigo):
    r = analisar(codigo)
    assert r["sucesso"] is False and r["ast"] is None
    assert len(r["erros"]) >= 1
    return r["erros"]


def sx(no):
    """AST -> tupla compacta: folhas viram texto, demais viram (TIPO, filhos...)."""
    t = no["tipo"]
    if t in LITERAIS:
        return no["atributos"]["valor"]
    if t == "IDENTIFICADOR":
        return no["atributos"]["nome"]
    return (t, *[sx(f) for f in no["filhos"]])


def expr(texto):
    """Estrutura da expressão `texto` analisada como valor de `x = texto;`."""
    ast = ok(f"x = {texto};")
    atrib = ast["filhos"][0]
    assert atrib["tipo"] == "ATRIBUICAO"
    return sx(atrib["filhos"][0])


def utf16(texto):
    return texto.encode("utf-16-le")


def trecho(codigo, no):
    return utf16(codigo)[no["inicio"] * 2:no["fim"] * 2].decode("utf-16-le")


def percorrer(no):
    yield no
    for f in no["filhos"]:
        yield from percorrer(f)


# ====================================================================== construções válidas
def test_programa_vazio_e_valido():
    ast = ok("")
    assert ast["tipo"] == "PROGRAMA" and ast["filhos"] == []
    assert (ast["linha"], ast["coluna"]) == (1, 1)


def test_somente_comentarios_e_valido():
    ast = ok("// nada\n/* aqui */")
    assert ast["filhos"] == []


def test_declaracao_sem_inicializacao():
    ast = ok("int x;")
    d = ast["filhos"][0]
    assert d["tipo"] == "DECLARACAO_VARIAVEL"
    assert d["atributos"] == {"tipo_dado": "int", "nome": "x"} and d["filhos"] == []


@pytest.mark.parametrize("tipo,valor", [("int", "10"), ("float", "2.5"), ("char", "'a'"), ("char", '"texto"')])
def test_declaracao_com_inicializacao_por_tipo(tipo, valor):
    d = ok(f"{tipo} v = {valor};")["filhos"][0]
    assert d["atributos"]["tipo_dado"] == tipo
    assert sx(d["filhos"][0]) == valor and d["filhos"][0]["papel"] == "valor"


def test_exemplo_da_especificacao_declaracao_com_precedencia():
    ast = ok("int resultado = 10 + 5 * 2;")
    d = ast["filhos"][0]
    assert d["atributos"] == {"tipo_dado": "int", "nome": "resultado"}
    assert sx(d) == ("DECLARACAO_VARIAVEL", ("ADICAO", "10", ("MULTIPLICACAO", "5", "2")))


def test_atribuicao():
    a = ok("x = y + 1;")["filhos"][0]
    assert a["tipo"] == "ATRIBUICAO" and a["atributos"] == {"nome": "x"}
    assert sx(a) == ("ATRIBUICAO", ("ADICAO", "y", "1"))


def test_if_sem_else():
    c = ok("if (a > 0) { b = 1; }")["filhos"][0]
    assert c["tipo"] == "CONDICIONAL" and c["atributos"] == {"tem_senao": False}
    assert [f["papel"] for f in c["filhos"]] == ["condicao", "entao"]
    assert sx(c["filhos"][0]) == ("COMPARACAO", "a", "0")


def test_if_com_else():
    c = ok("if (a) { b = 1; } else { b = 2; }")["filhos"][0]
    assert c["atributos"] == {"tem_senao": True}
    assert [f["papel"] for f in c["filhos"]] == ["condicao", "entao", "senao"]


def test_else_if_encadeado():
    c = ok("if (a) x = 1; else if (b) x = 2; else x = 3;")["filhos"][0]
    senao = c["filhos"][2]
    assert senao["tipo"] == "CONDICIONAL" and senao["atributos"]["tem_senao"] is True


def test_else_pertence_ao_if_mais_proximo():
    c = ok("if (a) if (b) x = 1; else x = 2;")["filhos"][0]
    assert c["atributos"]["tem_senao"] is False
    interno = c["filhos"][1]
    assert interno["tipo"] == "CONDICIONAL" and interno["atributos"]["tem_senao"] is True


def test_while():
    w = ok("while (i < 10) { i = i + 1; }")["filhos"][0]
    assert w["tipo"] == "REPETICAO" and [f["papel"] for f in w["filhos"]] == ["condicao", "corpo"]


def test_corpo_de_if_e_while_sem_chaves():
    ok("if (a) x = 1;")
    ok("while (a) x = x - 1;")


def test_return_com_e_sem_valor():
    assert ok("return 0;")["filhos"][0]["filhos"][0]["papel"] == "valor"
    assert ok("return;")["filhos"][0]["filhos"] == []


def test_blocos_aninhados():
    ast = ok("{ int a = 1; { int b = 2; { a = b; } } }")
    externo = ast["filhos"][0]
    assert externo["tipo"] == "BLOCO"
    assert [f["tipo"] for f in externo["filhos"]] == ["DECLARACAO_VARIAVEL", "BLOCO"]


def test_funcao_sem_parametros():
    f = ok("void ola() { return; }")["filhos"][0]
    assert f["tipo"] == "DEFINICAO_FUNCAO"
    assert f["atributos"] == {"tipo_retorno": "void", "nome": "ola"}
    assert [x["tipo"] for x in f["filhos"]] == ["BLOCO"]


def test_funcao_com_parametros():
    f = ok("int soma(int a, float b, char c) { return a; }")["filhos"][0]
    params = [x for x in f["filhos"] if x["tipo"] == "PARAMETRO"]
    assert [(p["atributos"]["tipo_dado"], p["atributos"]["nome"]) for p in params] == [
        ("int", "a"), ("float", "b"), ("char", "c")]
    assert f["filhos"][-1]["papel"] == "corpo"


def test_chamada_como_comando_e_como_expressao():
    ast = ok("f(1, 2);\nint r = g(h(3), x + 1);")
    assert sx(ast["filhos"][0]) == ("CHAMADA_FUNCAO", "1", "2")
    r = ast["filhos"][1]
    assert sx(r) == ("DECLARACAO_VARIAVEL", ("CHAMADA_FUNCAO", ("CHAMADA_FUNCAO", "3"), ("ADICAO", "x", "1")))
    assert r["filhos"][0]["atributos"] == {"nome": "g"}


def test_chamada_sem_argumentos():
    assert ok("f();")["filhos"][0]["filhos"] == []


def test_programa_completo_com_varios_itens():
    codigo = (
        "int fat(int n) {\n"
        "  if (n <= 1) { return 1; }\n"
        "  return n * fat(n - 1);\n"
        "}\n"
        "int resultado = fat(5);\n"
        "while (resultado > 0) { resultado = resultado - 10; }\n"
    )
    ast = ok(codigo)
    assert [f["tipo"] for f in ast["filhos"]] == ["DEFINICAO_FUNCAO", "DECLARACAO_VARIAVEL", "REPETICAO"]


def test_comandos_no_nivel_global_sao_aceitos_pela_gramatica():
    # decisão documentada: o programa é uma sequência de itens (declaracao | comando | funcao)
    ok("x = 1;\nif (x) { x = 2; }\nreturn 0;")


# ====================================================================== precedência e associatividade
def test_multiplicacao_antes_da_adicao():
    assert expr("2 + 3 * 4") == ("ADICAO", "2", ("MULTIPLICACAO", "3", "4"))
    assert expr("2 * 3 + 4") == ("ADICAO", ("MULTIPLICACAO", "2", "3"), "4")


def test_subtracao_associa_a_esquerda():
    assert expr("20 - 5 - 3") == ("SUBTRACAO", ("SUBTRACAO", "20", "5"), "3")
    assert expr("10 - 3 - 2") == ("SUBTRACAO", ("SUBTRACAO", "10", "3"), "2")


def test_divisao_e_modulo_associam_a_esquerda():
    assert expr("8 / 4 / 2") == ("DIVISAO", ("DIVISAO", "8", "4"), "2")
    assert expr("9 % 4 % 3") == ("MODULO", ("MODULO", "9", "4"), "3")
    assert expr("a * b / c % d") == ("MODULO", ("DIVISAO", ("MULTIPLICACAO", "a", "b"), "c"), "d")


def test_parenteses_alteram_a_organizacao():
    assert expr("(10 + 5) * 2") == ("MULTIPLICACAO", ("ADICAO", "10", "5"), "2")
    assert expr("2 * (3 + 4)") == ("MULTIPLICACAO", "2", ("ADICAO", "3", "4"))
    assert expr("((7))") == "7"
    assert expr("10 - (5 - 3)") == ("SUBTRACAO", "10", ("SUBTRACAO", "5", "3"))


def test_adicao_e_subtracao_misturadas():
    assert expr("1 + 2 - 3 + 4") == ("ADICAO", ("SUBTRACAO", ("ADICAO", "1", "2"), "3"), "4")


def test_relacionais_tem_menor_precedencia_que_aritmetica():
    assert expr("a + 1 < b * 2") == ("COMPARACAO", ("ADICAO", "a", "1"), ("MULTIPLICACAO", "b", "2"))


def test_igualdade_tem_menor_precedencia_que_relacional():
    assert expr("a == b < c") == ("COMPARACAO", "a", ("COMPARACAO", "b", "c"))
    assert expr("a < b == c < d") == ("COMPARACAO", ("COMPARACAO", "a", "b"), ("COMPARACAO", "c", "d"))


def test_e_tem_precedencia_maior_que_ou():
    assert expr("a || b && c") == ("OPERACAO_LOGICA", "a", ("OPERACAO_LOGICA", "b", "c"))
    ast = ok("x = a || b && c;")
    ou = ast["filhos"][0]["filhos"][0]
    assert ou["atributos"]["operador"] == "||" and ou["filhos"][1]["atributos"]["operador"] == "&&"


def test_operadores_logicos_associam_a_esquerda():
    ast = ok("x = a && b && c;")
    topo = ast["filhos"][0]["filhos"][0]
    assert sx(topo) == ("OPERACAO_LOGICA", ("OPERACAO_LOGICA", "a", "b"), "c")


def test_comparacao_com_logicos():
    assert expr("a > 0 && b < 10 || c == 1") == (
        "OPERACAO_LOGICA",
        ("OPERACAO_LOGICA", ("COMPARACAO", "a", "0"), ("COMPARACAO", "b", "10")),
        ("COMPARACAO", "c", "1"),
    )


def test_unarios_tem_maior_precedencia():
    assert expr("-a * b") == ("MULTIPLICACAO", ("MENOS_UNARIO", "a"), "b")
    assert expr("!a && b") == ("OPERACAO_LOGICA", ("NEGACAO_LOGICA", "a"), "b")
    assert expr("!a == b") == ("COMPARACAO", ("NEGACAO_LOGICA", "a"), "b")


def test_unarios_encadeados_associam_a_direita():
    assert expr("- - a") == ("MENOS_UNARIO", ("MENOS_UNARIO", "a"))
    assert expr("!!a") == ("NEGACAO_LOGICA", ("NEGACAO_LOGICA", "a"))
    assert expr("-!a") == ("MENOS_UNARIO", ("NEGACAO_LOGICA", "a"))


def test_menos_binario_e_unario_juntos():
    assert expr("a - -b") == ("SUBTRACAO", "a", ("MENOS_UNARIO", "b"))
    assert expr("a--b") == ("SUBTRACAO", "a", ("MENOS_UNARIO", "b"))
    assert expr("-a - b") == ("SUBTRACAO", ("MENOS_UNARIO", "a"), "b")


def test_chamadas_em_expressoes_respeitam_precedencia():
    assert expr("f(1) + g(2) * 3") == ("ADICAO", ("CHAMADA_FUNCAO", "1"), ("MULTIPLICACAO", ("CHAMADA_FUNCAO", "2"), "3"))


def test_literais_de_todos_os_tipos_em_expressoes():
    assert expr('1 + 2.5') == ("ADICAO", "1", "2.5")
    assert expr("'a'") == "'a'" and expr('"s"') == '"s"'


def _gerar_expressao(rng, prof):
    if prof == 0 or rng.random() < 0.25:
        return str(rng.randint(0, 9))
    k = rng.random()
    if k < 0.2:
        return f"({_gerar_expressao(rng, prof - 1)})"
    if k < 0.3:
        return f"-{_gerar_expressao(rng, prof - 1)}"
    op = rng.choice(["+", "-", "*"])
    return f"{_gerar_expressao(rng, prof - 1)} {op} {_gerar_expressao(rng, prof - 1)}"


def _avaliar(no):
    t = no["tipo"]
    if t == "LITERAL_INTEIRO":
        return int(no["atributos"]["valor"])
    f = [_avaliar(x) for x in no["filhos"]]
    return {"ADICAO": lambda: f[0] + f[1], "SUBTRACAO": lambda: f[0] - f[1],
            "MULTIPLICACAO": lambda: f[0] * f[1], "MENOS_UNARIO": lambda: -f[0]}[t]()


def test_propriedade_avaliar_a_ast_equivale_a_avaliar_o_texto():
    """Verificação independente: o valor calculado pela AST bate com o do Python (mesma precedência)."""
    rng = random.Random(20261111)
    for _ in range(400):
        texto = _gerar_expressao(rng, 5)
        esperado = eval(texto)  # noqa: S307  (só dígitos, + - * e parênteses gerados pelo teste)
        ast = ok(f"x = {texto};")
        assert _avaliar(ast["filhos"][0]["filhos"][0]) == esperado, texto


# ====================================================================== estrutura, ids e posições
def test_todos_os_nos_seguem_o_mesmo_formato():
    ast = ok("int f(int a) { if (a > 0 && !a) { return -a * 2; } return g(a, 'x'); }")
    for no in percorrer(ast):
        assert set(no) == {"tipo", "id", "papel", "linha", "coluna", "fim_linha", "fim_coluna",
                           "inicio", "fim", "atributos", "filhos"}
        assert isinstance(no["atributos"], dict) and isinstance(no["filhos"], list)


def test_ids_unicos_e_em_pre_ordem():
    ast = ok("int a = 1 + 2 * 3;\nint b = (a - 1) * 2;")
    ids = [n["id"] for n in percorrer(ast)]
    assert ids == list(range(1, len(ids) + 1))


def test_raiz_nao_tem_papel_e_filhos_tem():
    ast = ok("int a = 1 + 2;")
    assert ast["papel"] is None
    assert all(n["papel"] for n in percorrer(ast) if n is not ast)


def test_trechos_dos_nos_correspondem_ao_codigo():
    codigo = "int resultado = 10 + 5 * 2;\nif (resultado > 3) { resultado = 0; }"
    ast = ok(codigo)
    decl, cond = ast["filhos"]
    assert trecho(codigo, decl) == "int resultado = 10 + 5 * 2;"
    assert trecho(codigo, decl["filhos"][0]) == "10 + 5 * 2"
    assert trecho(codigo, decl["filhos"][0]["filhos"][1]) == "5 * 2"
    assert trecho(codigo, cond) == "if (resultado > 3) { resultado = 0; }"
    assert trecho(codigo, cond["filhos"][0]) == "resultado > 3"
    assert trecho(codigo, cond["filhos"][1]) == "{ resultado = 0; }"


def test_no_entre_parenteses_inclui_os_parenteses_no_trecho_mas_nao_vira_no():
    codigo = "x = (1 + 2) * 3;"
    mult = ok(codigo)["filhos"][0]["filhos"][0]
    soma = mult["filhos"][0]
    assert soma["tipo"] == "ADICAO" and trecho(codigo, soma) == "(1 + 2)"
    assert trecho(codigo, mult) == "(1 + 2) * 3"


def test_linha_e_coluna_inicial_e_final_dos_nos():
    codigo = "int a = 1;\nint b =\n  a + 2;"
    ast = ok(codigo)
    a, b = ast["filhos"]
    assert (a["linha"], a["coluna"], a["fim_linha"], a["fim_coluna"]) == (1, 1, 1, 11)
    assert (b["linha"], b["coluna"], b["fim_linha"], b["fim_coluna"]) == (2, 1, 3, 9)
    soma = b["filhos"][0]
    assert (soma["linha"], soma["coluna"]) == (3, 3)


def test_posicoes_com_emoji_usam_caracteres_para_linha_coluna_e_utf16_para_deslocamentos():
    codigo = 'char s = "😀"; int x;'
    ast = ok(codigo)
    x = ast["filhos"][1]
    assert x["coluna"] == 15  # 14 caracteres antes
    assert trecho(codigo, x) == "int x;"


def test_valores_longos_nao_sao_truncados_na_ast():
    longo = "a" * 100
    ast = ok(f"{longo} = 1;")
    assert ast["filhos"][0]["atributos"]["nome"] == longo
    texto = "x" * 60
    ast = ok(f'char s = "{texto}";')
    assert ast["filhos"][0]["filhos"][0]["atributos"]["valor"] == f'"{texto}"'


def test_programa_ocupa_do_primeiro_ao_ultimo_token():
    codigo = "  int a;  // fim\n"
    ast = ok(codigo)
    assert (ast["linha"], ast["coluna"]) == (1, 3) and trecho(codigo, ast) == "int a;"


def test_filhos_ficam_dentro_do_pai_e_em_ordem():
    codigo = "int f(int a, int b) { while (a < b) { a = a + 1; } return a; }"
    ast = ok(codigo)
    for no in percorrer(ast):
        ant = no["inicio"]
        for f in no["filhos"]:
            assert no["inicio"] <= f["inicio"] and f["fim"] <= no["fim"]
            assert f["inicio"] >= ant
            ant = f["fim"]


def test_folhas_da_ast_correspondem_a_tokens_do_scanner():
    """Consistência entre visualizações: cada folha da AST é exatamente um token da tabela."""
    codigo = "int soma(int a, int b) { return a + b * 2; }\nint r = soma(1, 2.5);"
    lex = tokenizar(codigo)
    ast = analisar_sintaxe(lex["tokens"], codigo)["ast"]
    por_pos = {(t["inicio"], t["fim"]): t for t in lex["tokens"]}
    for no in percorrer(ast):
        if no["tipo"] == "IDENTIFICADOR" or no["tipo"] in LITERAIS:
            tk = por_pos[(no["inicio"], no["fim"])]
            assert (tk["linha"], tk["coluna"]) == (no["linha"], no["coluna"])
            assert tk["tipo"] == no["tipo"]


def test_todos_os_tokens_ficam_dentro_do_programa():
    codigo = "int a = 1; if (a) { a = 2; }"
    lex = tokenizar(codigo)
    ast = analisar_sintaxe(lex["tokens"], codigo)["ast"]
    assert all(ast["inicio"] <= t["inicio"] and t["fim"] <= ast["fim"] for t in lex["tokens"])


def test_resumo_e_regras():
    r = analisar("int a = 1 + 2;")
    assert r["resumo"] == {"total_nos": 5, "altura": 4,
                           "por_tipo": {"PROGRAMA": 1, "DECLARACAO_VARIAVEL": 1, "ADICAO": 1, "LITERAL_INTEIRO": 2}}
    assert set(r["regras"]) == set(r["resumo"]["por_tipo"])
    assert r["regras"]["ADICAO"]["categoria"] == "expressao"
    assert "soma = termo" in r["regras"]["ADICAO"]["regra"]


def test_texto_da_arvore():
    texto = analisar("int a = 1 + 2;")["texto"]
    linhas = texto.split("\n")
    assert linhas[0].startswith("PROGRAMA")
    assert linhas[1].startswith("└── item: DECLARACAO_VARIAVEL")
    assert any("ADICAO" in l for l in linhas) and any("valor=1" in l for l in linhas)


def test_mensagem_de_sucesso():
    assert analisar("int a;")["mensagem"] == "Análise sintática concluída: programa válido (AST com 2 nós)."
    assert "programa vazio" in analisar("")["mensagem"]


# ====================================================================== erros sintáticos
def test_erro_do_exemplo_da_especificacao_ponto_e_virgula_antes_de_chave():
    e = erros("int numero = 10}")[0]  # sem espaço: o '}' fica na coluna 16, como no exemplo do enunciado
    assert e["tipo"] == "ERRO_SINTATICO"
    assert (e["linha"], e["coluna"]) == (1, 16)
    assert e["encontrado"] == "}" and e["esperado"] == [";"]
    assert e["mensagem"] == "Era esperado ';' ao final da declaração, mas foi encontrado '}'."
    assert e["regra"].startswith("declaracao =")


def test_posicao_do_erro_com_espaco_antes_da_chave():
    e = erros("int numero = 10 }")[0]
    assert (e["linha"], e["coluna"]) == (1, 17)


def test_formato_completo_do_erro():
    e = erros("int x = 5")[0]
    assert set(e) == {"tipo", "linha", "coluna", "inicio", "fim", "encontrado", "encontrado_tipo",
                      "esperado", "mensagem", "regra", "dica"}


def test_ponto_e_virgula_ausente_no_fim_do_codigo():
    e = erros("int x = 5 + 3")[0]
    assert e["encontrado"] == "fim do código" and e["encontrado_tipo"] == "FIM"
    assert "o código terminou antes disso" in e["mensagem"]
    assert (e["linha"], e["coluna"]) == (1, 14)


def test_ponto_e_virgula_ausente_aponta_dica_da_linha_anterior():
    e = erros("int x = 5\nint y = 6;")[0]
    assert (e["linha"], e["coluna"]) == (2, 1)
    assert "fim da linha anterior" in e["dica"]


@pytest.mark.parametrize(
    "codigo,trecho_msg",
    [
        ("x = 5", "ao final da atribuição"),
        ("return 1", "ao final do return"),
        ("f(1)", "ao final da chamada de função"),
    ],
)
def test_ponto_e_virgula_ausente_em_outras_instrucoes(codigo, trecho_msg):
    e = erros(codigo)[0]
    assert trecho_msg in e["mensagem"] and e["esperado"] == [";"]


def test_parenteses_da_condicao_do_if():
    e = erros("if (x > 0 { y = 1; }")[0]
    assert e["mensagem"] == "Era esperado ')' para fechar a condição do if, mas foi encontrado '{'."
    assert e["esperado"] == [")"] and (e["linha"], e["coluna"]) == (1, 11)
    assert e["regra"].startswith("condicional =")
    e = erros("if x > 0) { }")[0]
    assert "Era esperado '(' depois de 'if'" in e["mensagem"]


def test_parenteses_da_condicao_do_while():
    e = erros("while (a < b { }")[0]
    assert "para fechar a condição do while" in e["mensagem"]


def test_condicao_vazia():
    e = erros("if () { }")[0]
    assert "Era esperada uma expressão na condição do if" in e["mensagem"] and e["encontrado"] == ")"


def test_expressao_sem_operando_depois_de_operador():
    e = erros("int y = x + ;")[0]
    assert e["mensagem"] == "Era esperada uma expressão depois do operador '+', mas foi encontrado ';'."
    assert "IDENTIFICADOR" in e["esperado"] and "(" in e["esperado"]


def test_operadores_consecutivos():
    e = erros("int x = 1 + * 2;")[0]
    assert e["mensagem"].startswith("Operadores consecutivos")
    assert "'*'" in e["mensagem"] and (e["linha"], e["coluna"]) == (1, 13)


def test_atribuicao_sem_valor():
    e = erros("x = ;")[0]
    assert "depois de '=' na atribuição a 'x'" in e["mensagem"]


def test_declaracao_sem_valor_depois_do_igual():
    e = erros("int x = ;")[0]
    assert "depois de '=' na declaração de 'x'" in e["mensagem"]


def test_parentese_nao_fechado_na_expressao_aponta_onde_abriu():
    e = erros("int x = (1 + 2;")[0]
    assert e["mensagem"] == "Era esperado ')' para fechar o '(' aberto na linha 1, coluna 9, mas foi encontrado ';'."


def test_else_sem_if():
    e = erros("else { x = 1; }")[0]
    assert e["mensagem"].startswith("'else' sem 'if' correspondente")
    assert (e["linha"], e["coluna"]) == (1, 1)


def test_else_sem_if_depois_de_if_completo_com_ponto_e_virgula_extra():
    es = erros("if (a) x = 1;; else x = 2;")
    assert any("sem 'if'" in e["mensagem"] or "sozinho" in e["mensagem"] for e in es)


def test_palavra_reservada_no_lugar_de_identificador():
    es = erros("int while = 5;")
    assert len(es) == 1  # sem erro em cascata
    assert es[0]["mensagem"].startswith("Era esperado um nome (identificador) depois do tipo 'int'")
    assert "palavra reservada" in es[0]["mensagem"] and (es[0]["linha"], es[0]["coluna"]) == (1, 5)


def test_palavra_reservada_como_valor():
    e = erros("x = int;")[0]
    assert "palavra reservada" in e["mensagem"]


def test_instrucao_que_comeca_com_literal():
    e = erros("10;")[0]
    assert "Uma instrução não pode começar com o número 10" in e["mensagem"]


def test_nome_seguido_de_algo_invalido():
    e = erros("x 5;")[0]
    assert e["esperado"] == ["=", "("] and (e["linha"], e["coluna"]) == (1, 3)


def test_chave_e_parentese_sobrando():
    assert "'}' sem '{' correspondente" in erros("int a; }")[0]["mensagem"]
    assert "')' sem '(' correspondente" in erros("x = 1; )")[0]["mensagem"]


def test_ponto_e_virgula_sozinho():
    e = erros("int x = 1;;")[0]
    assert "';' sozinho" in e["mensagem"]


def test_colchetes_nao_fazem_parte_da_gramatica():
    e = erros("int a[3];")[0]
    assert "colchetes" in e["dica"]


def test_declaracao_no_corpo_de_if_sem_chaves():
    e = erros("if (x) int y = 1;")[0]
    assert "dentro de um bloco" in e["mensagem"] and e["esperado"] == ["{"]


def test_funcao_dentro_de_bloco():
    es = erros("int f() { int g() { } }")
    assert len(es) == 1 and "Funções só podem ser definidas fora de blocos" in es[0]["mensagem"]


def test_prototipo_de_funcao_nao_suportado():
    e = erros("int f(int a);")[0]
    assert "iniciar o corpo da função 'f'" in e["mensagem"] and "Protótipos" in e["dica"]


def test_void_como_tipo_de_variavel():
    e = erros("void v;")[0]
    assert "'void' só pode ser usado como tipo de retorno" in e["mensagem"]


def test_parametro_sem_tipo_e_parametro_void():
    assert "Era esperado o tipo do parâmetro" in erros("int f(int a, b) { }")[0]["mensagem"]
    assert "'void' não pode ser tipo de parâmetro" in erros("int f(void) { }")[0]["mensagem"]


def test_lista_de_parametros_mal_formada():
    e = erros("int f(int a int b) { }")[0]
    assert e["esperado"] == [",", ")"] and "lista de parâmetros da função 'f'" in e["mensagem"]


def test_lista_de_argumentos_mal_formada():
    e = erros("f(1 2);")[0]
    assert e["esperado"] == [",", ")"] and "argumentos da chamada de 'f'" in e["mensagem"]


def test_argumento_vazio_depois_de_virgula():
    e = erros("f(1, );")[0]
    assert "no argumento da chamada de 'f'" in e["mensagem"]


def test_return_sem_ponto_e_virgula_no_fim_do_codigo():
    e = erros("return")[0]
    assert "depois de 'return'" in e["mensagem"]


# -------------------------------------------------------------- fim inesperado / blocos
def test_bloco_nao_fechado():
    e = erros("int a;\n{ int x = 1;\n")[0]
    assert e["mensagem"] == "O código terminou antes de o bloco aberto na linha 2 ser fechado com '}'."
    assert e["esperado"] == ["}"] and e["encontrado_tipo"] == "FIM"
    assert (e["linha"], e["coluna"]) == (3, 1)


def test_varios_blocos_nao_fechados_geram_um_unico_erro():
    es = erros("{\n  {\n    int x = 1;")
    assert len(es) == 1
    assert "2 blocos abertos" in es[0]["mensagem"] and "linhas 1, 2" in es[0]["mensagem"]


def test_funcao_com_corpo_nao_fechado():
    e = erros("int f() {\n  return 1;\n")[0]
    assert "bloco aberto na linha 1" in e["mensagem"]


def test_fim_do_codigo_no_meio_de_construcoes():
    for codigo in ["if (", "if (x", "while", "int", "int x =", "x =", "f(", "int f(", "int f(int", "x = (1 +"]:
        es = erros(codigo)
        assert es[-1]["encontrado_tipo"] == "FIM", codigo


# -------------------------------------------------------------- recuperação de erros
def test_varios_erros_independentes_sao_acumulados():
    es = erros("int a = ;\nx = 5\nif (y {\n}\nint z = 1 +;")
    linhas = [e["linha"] for e in es]
    assert linhas[0] == 1 and 3 in linhas and 5 in linhas
    assert len(es) >= 3


def test_recuperacao_continua_na_proxima_instrucao():
    es = erros("int a = ;\nint b = 1;\nint c = ;")
    assert [e["linha"] for e in es] == [1, 3]


def test_recuperacao_dentro_de_bloco_nao_derruba_o_bloco():
    es = erros("{ int a = ; int b = 2; int c = ; }")
    assert len(es) == 2  # o bloco continua valendo: sem erro de '}' sobrando


def test_erro_em_if_nao_gera_else_orfao_em_cascata():
    es = erros("if (x > 0 { y = 1; } else { y = 2; }")
    assert len(es) == 1


def test_ponto_e_virgula_esquecido_nao_engole_a_proxima_instrucao():
    es = erros("int x = 10\nint y = x + ;\nz = 5;")
    assert [(e["linha"], e["coluna"]) for e in es] == [(2, 1), (2, 13)]


def test_nao_ha_erro_em_cascata_nos_casos_tipicos():
    casos = {
        "int while = 5;": 1,
        "int f() { int g() { } }": 1,
        "if (x) int y = 1;": 1,
        "int x = 1 + * 2;": 1,
        "else { x = 1; }": 1,
        "x = ;": 1,
        "int x = (1 + 2;": 1,
    }
    for codigo, quantidade in casos.items():
        assert len(erros(codigo)) == quantidade, codigo


def test_limite_de_erros():
    codigo = "\n".join(["x = ;"] * 30)
    r = analisar(codigo)
    assert len(r["erros"]) == LIMITE_ERROS and r["erros_truncados"] is True
    assert "limite de 10 erros" in r["mensagem"]


def test_apenas_um_erro_de_fim_de_codigo():
    es = erros("{ { if (x")
    assert sum(1 for e in es if e["encontrado_tipo"] == "FIM") == 1


def test_ast_e_erros_sao_mutuamente_exclusivos():
    r = analisar("int a = 1;")
    assert r["ast"] is not None and r["erros"] == []
    r = analisar("int a = ;")
    assert r["ast"] is None and r["erros"] and r["resumo"] is None and r["texto"] is None and r["regras"] == {}


# ====================================================================== limites e robustez
def test_aninhamento_dentro_do_limite_e_aceito():
    n = LIMITE_ANINHAMENTO
    ok(f"x = {'(' * n}1{')' * n};")


def test_aninhamento_acima_do_limite_gera_erro_e_nao_excecao():
    n = LIMITE_ANINHAMENTO + 1
    e = erros(f"x = {'(' * n}1{')' * n};")[0]
    assert "aninhamento profundo demais" in e["mensagem"]


def test_aninhamento_gigante_nao_estoura_a_pilha():
    for codigo in ["x = " + "(" * 5000 + "1;", "x = " + "!" * 5000 + "a;", "{" * 3000, "if (a) " * 3000]:
        r = analisar_sintaxe(tokenizar(codigo)["tokens"], codigo)
        assert r["sucesso"] is False and r["erros"]


def test_cadeia_longa_de_operadores_acima_da_altura_maxima():
    r = analisar("x = " + " + ".join(["1"] * 400) + ";")
    assert r["sucesso"] is False
    assert f"mais de {LIMITE_ALTURA} níveis" in r["erros"][0]["mensagem"]


def test_cadeia_de_operadores_dentro_da_altura_maxima():
    r = analisar("x = " + " + ".join(["1"] * 100) + ";")
    assert r["sucesso"] is True and r["resumo"]["altura"] <= LIMITE_ALTURA


def test_entrada_grande_e_rapida():
    codigo = "int a = 1 + 2 * 3;\n" * 1000
    inicio = time.perf_counter()
    r = analisar(codigo)
    assert time.perf_counter() - inicio < 3.0
    assert r["sucesso"] and r["resumo"]["total_nos"] > 5000 and r["texto"] is None  # texto só para árvores pequenas


def test_texto_so_para_arvores_pequenas():
    assert analisar("int a = 1;")["texto"] is not None


def test_nao_executa_parser_com_lista_vazia_de_tokens_com_texto_residual():
    assert analisar_sintaxe([], "   // nada")["sucesso"] is True


_VOCABULARIO = ["int", "float", "char", "void", "if", "else", "while", "return", "x", "y", "f", "1", "2.5",
                '"s"', "'c'", "+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">=", "&&", "||", "!", "=",
                "(", ")", "{", "}", "[", "]", ";", ","]


def test_fuzz_sequencias_aleatorias_de_tokens_sempre_terminam_de_forma_consistente():
    rng = random.Random(4242)
    inicio = time.perf_counter()
    for _ in range(800):
        codigo = " ".join(rng.choice(_VOCABULARIO) for _ in range(rng.randint(0, 40)))
        lex = tokenizar(codigo)
        r = analisar_sintaxe(lex["tokens"], codigo)
        assert (r["ast"] is not None) == r["sucesso"] == (not r["erros"]), codigo
        assert len(r["erros"]) <= LIMITE_ERROS, codigo
        for e in r["erros"]:
            assert e["mensagem"] and e["linha"] >= 1 and e["coluna"] >= 1
    assert time.perf_counter() - inicio < 20


def test_fuzz_programas_validos_gerados_sao_aceitos():
    """Programas montados a partir da gramática devem sempre ser aceitos (não só os exemplos do projeto)."""
    rng = random.Random(7)

    def e(p):
        return _gerar_expressao(rng, p)

    def cmd(p):
        k = rng.randint(0, 6)
        if p == 0 or k == 0:
            return f"v = {e(2)};"
        if k == 1:
            return f"int n{rng.randint(0, 9)} = {e(2)};"
        if k == 2:
            return f"if ({e(2)} < {e(1)}) {{ {cmd(p - 1)} }} else {{ {cmd(p - 1)} }}"
        if k == 3:
            return f"while ({e(1)} != 0) {{ {cmd(p - 1)} {cmd(p - 1)} }}"
        if k == 4:
            return f"f({e(1)}, {e(1)});"
        if k == 5:
            return f"return {e(2)};"
        return f"{{ {cmd(p - 1)} }}"

    for _ in range(200):
        codigo = "int f(int a, int b) { " + cmd(3) + " }\n" + cmd(3)
        r = analisar(codigo)
        assert r["sucesso"], (codigo, [x["mensagem"] for x in r["erros"]])


# ====================================================================== integração com o scanner
def test_parser_consome_exatamente_os_tokens_do_scanner():
    codigo = "int a = 1; // c\nfloat b = a * 2.5;"
    lex = tokenizar(codigo)
    r = analisar_sintaxe(lex["tokens"], codigo)
    assert r["sucesso"] is True
    assert lex["resumo"]["total_tokens"] == 12  # a AST cobre todos eles (verificado em outro teste)


def test_scanner_continua_produzindo_os_mesmos_tokens_apos_a_etapa_4():
    r = tokenizar("int numero = 10;")
    assert [(t["tipo"], t["lexema"], t["linha"], t["coluna"]) for t in r["tokens"]] == [
        ("PALAVRA_RESERVADA", "int", 1, 1), ("IDENTIFICADOR", "numero", 1, 5),
        ("OPERADOR_ATRIBUICAO", "=", 1, 12), ("LITERAL_INTEIRO", "10", 1, 14), ("DELIMITADOR", ";", 1, 16)]


def test_concordancia_de_genero_nas_mensagens():
    # "foi encontrada a palavra reservada" / "a string" (feminino); "foi encontrado o identificador/número" (masculino)
    assert "foi encontrada a palavra reservada 'int'" in erros("int x = 10\nint y = 5;")[0]["mensagem"]
    assert 'foi encontrada a string "a"' in erros('int x = 1 "a";')[0]["mensagem"]
    assert "foi encontrado o identificador 'y'" in erros("int x = 1 y;")[0]["mensagem"]
    assert "foi encontrado o número 5" in erros("int x = 1 5;")[0]["mensagem"]
    assert "foi encontrado o caractere 'c'" in erros("int x = 1 'c';")[0]["mensagem"]
