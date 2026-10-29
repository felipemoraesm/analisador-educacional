import pytest

from app.scanner import CATEGORIAS, PALAVRAS_RESERVADAS, tokenizar


def tipos(codigo):
    return [t["tipo"] for t in tokenizar(codigo)["tokens"]]


def lexemas(codigo):
    return [t["lexema"] for t in tokenizar(codigo)["tokens"]]


def par(codigo):
    return [(t["tipo"], t["lexema"]) for t in tokenizar(codigo)["tokens"]]


def utf16(texto):
    return texto.encode("utf-16-le")


def fatia(codigo, item):
    """Trecho do código indicado por inicio/fim (unidades UTF-16)."""
    return utf16(codigo)[item["inicio"] * 2:item["fim"] * 2].decode("utf-16-le")


# ---------------- Palavras reservadas ----------------
@pytest.mark.parametrize("palavra", PALAVRAS_RESERVADAS)
def test_cada_palavra_reservada_e_reconhecida(palavra):
    assert par(palavra) == [("PALAVRA_RESERVADA", palavra)]


def test_conjunto_de_palavras_reservadas_documentado():
    assert set(PALAVRAS_RESERVADAS) == {"int", "float", "char", "if", "else", "while", "return"}


@pytest.mark.parametrize("texto", ["integer", "Int", "IF", "iff", "returns", "int1", "_int", "whiles"])
def test_palavra_reservada_so_vale_para_lexema_inteiro(texto):
    assert par(texto) == [("IDENTIFICADOR", texto)]


# ---------------- Identificadores ----------------
@pytest.mark.parametrize("nome", ["numero", "_x1", "x", "A", "_", "__", "nome_completo", "valor2", "a1b2c3", "CamelCase"])
def test_identificadores_validos(nome):
    assert par(nome) == [("IDENTIFICADOR", nome)]


def test_identificador_termina_no_primeiro_caractere_invalido():
    r = tokenizar("abc-def")
    assert [t["lexema"] for t in r["tokens"]] == ["abc", "-", "def"]


@pytest.mark.parametrize("texto", ["1x", "2abc", "9_a"])
def test_identificador_iniciando_com_digito_e_erro(texto):
    r = tokenizar(texto)
    assert r["tokens"] == []
    assert r["erros"][0]["lexema"] == texto
    assert "identificador" in r["erros"][0]["mensagem"]


def test_identificador_com_letra_acentuada_gera_erro_no_acento():
    r = tokenizar("ação")
    assert [t["lexema"] for t in r["tokens"]] == ["a", "o"]
    assert [e["lexema"] for e in r["erros"]] == ["ç", "ã"]
    assert "sem acento" in r["erros"][0]["dica"]


# ---------------- Literais ----------------
@pytest.mark.parametrize("texto", ["0", "10", "42", "007", "1234567890"])
def test_literais_inteiros(texto):
    assert par(texto) == [("LITERAL_INTEIRO", texto)]


@pytest.mark.parametrize("texto", ["3.14", "0.5", "10.0", "123.456"])
def test_literais_reais(texto):
    assert par(texto) == [("LITERAL_REAL", texto)]


@pytest.mark.parametrize("texto", ['"abc"', '""', '"ola mundo"', '"a\\nb"', '"aspas \\" dentro"', '"// nao e comentario"', '"/* nem este */"', '"ação ✓"'])
def test_literais_string(texto):
    assert par(texto) == [("LITERAL_STRING", texto)]


@pytest.mark.parametrize("texto", ["'a'", "'Z'", "'0'", "' '", "'\\n'", "'\\t'", "'\\0'", "'\\\\'", "'\\''", "'\"'"])
def test_literais_caractere(texto):
    assert par(texto) == [("LITERAL_CHAR", texto)]


@pytest.mark.parametrize(
    "texto,trecho_msg",
    [
        ("3.", "faltam dígitos"),
        ("1.2.3", "apenas um ponto"),
        ("12abc", "identificador"),
        ("0x1F", "hexadecimais"),
        ("1e5", "científica"),
        ("2.5e3", "científica"),
        ("7..8", "malformado"),
    ],
)
def test_numeros_malformados(texto, trecho_msg):
    r = tokenizar(texto)
    assert r["tokens"] == []
    assert len(r["erros"]) == 1
    assert r["erros"][0]["lexema"] == texto
    assert trecho_msg in r["erros"][0]["mensagem"]


def test_ponto_sozinho_e_erro_e_o_numero_depois_continua_valido():
    r = tokenizar(".5")
    assert [e["lexema"] for e in r["erros"]] == ["."]
    assert par(".5") == [("LITERAL_INTEIRO", "5")]
    assert "0.5" in r["erros"][0]["dica"]


@pytest.mark.parametrize(
    "texto,trecho",
    [
        ('"aberta', "String não fechada"),
        ('"termina com barra\\', "String não fechada"),
        ('"escape \\q ruim"', "escape inválida"),
        ("'a", "não fechado"),
        ("''", "vazio"),
        ("'ab'", "mais de um caractere"),
        ("'\\q'", "escape inválida"),
    ],
)
def test_literais_texto_malformados(texto, trecho):
    r = tokenizar(texto)
    assert r["tokens"] == []
    assert len(r["erros"]) == 1
    assert trecho in r["erros"][0]["mensagem"]


def test_string_nao_fechada_termina_no_fim_da_linha_e_o_resto_e_tokenizado():
    r = tokenizar('x = "abc\nint y;')
    assert [e["lexema"] for e in r["erros"]] == ['"abc']
    assert r["erros"][0]["linha"] == 1
    assert [t["lexema"] for t in r["tokens"]] == ["x", "=", "int", "y", ";"]
    assert r["tokens"][2]["linha"] == 2


# ---------------- Operadores ----------------
@pytest.mark.parametrize("op", ["+", "-", "*", "/", "%"])
def test_operadores_aritmeticos(op):
    assert par(op) == [("OPERADOR_ARITMETICO", op)]


@pytest.mark.parametrize("op", ["==", "!=", "<", ">", "<=", ">="])
def test_operadores_relacionais(op):
    assert par(op) == [("OPERADOR_RELACIONAL", op)]


@pytest.mark.parametrize("op", ["&&", "||", "!"])
def test_operadores_logicos(op):
    assert par(op) == [("OPERADOR_LOGICO", op)]


def test_operador_de_atribuicao():
    assert par("=") == [("OPERADOR_ATRIBUICAO", "=")]


@pytest.mark.parametrize(
    "codigo,esperado",
    [
        ("a<=b", ["a", "<=", "b"]),
        ("a<b", ["a", "<", "b"]),
        ("a>=b", ["a", ">=", "b"]),
        ("a==b", ["a", "==", "b"]),
        ("a=b", ["a", "=", "b"]),
        ("a!=b", ["a", "!=", "b"]),
        ("!a", ["!", "a"]),
        ("a===b", ["a", "==", "=", "b"]),       # maior casamento, da esquerda para a direita
        ("a<==b", ["a", "<=", "=", "b"]),
        ("a=-1", ["a", "=", "-", "1"]),
        ("a=!b", ["a", "=", "!", "b"]),
        ("a&&!b", ["a", "&&", "!", "b"]),
        ("a/b", ["a", "/", "b"]),
    ],
)
def test_maior_casamento_dos_operadores(codigo, esperado):
    assert lexemas(codigo) == esperado


@pytest.mark.parametrize("texto,dica", [("&", "&&"), ("|", "||")])
def test_e_ou_sozinhos_sao_erro_com_dica(texto, dica):
    r = tokenizar(f"a {texto} b")
    assert [e["lexema"] for e in r["erros"]] == [texto]
    assert dica in r["erros"][0]["dica"]
    assert [t["lexema"] for t in r["tokens"]] == ["a", "b"]


# ---------------- Delimitadores ----------------
@pytest.mark.parametrize("d", list("(){}[];,"))
def test_delimitadores(d):
    assert par(d) == [("DELIMITADOR", d)]


# ---------------- Comentários e espaços ----------------
def test_comentario_de_linha_e_ignorado():
    r = tokenizar("int a; // comentario aqui\nint b;")
    assert [t["lexema"] for t in r["tokens"]] == ["int", "a", ";", "int", "b", ";"]
    assert r["comentarios"][0]["tipo"] == "COMENTARIO_LINHA"
    assert r["comentarios"][0]["lexema"] == "// comentario aqui"
    assert r["sucesso"] is True


def test_comentario_de_bloco_multilinha_e_ignorado_e_linhas_continuam_corretas():
    r = tokenizar("int a; /* linha 1\nlinha 2\nlinha 3 */ int b;")
    assert [t["lexema"] for t in r["tokens"]] == ["int", "a", ";", "int", "b", ";"]
    ultimo = r["tokens"][3]
    assert (ultimo["linha"], ultimo["coluna"]) == (3, 12)
    assert r["comentarios"][0]["tipo"] == "COMENTARIO_BLOCO"


def test_comentario_de_bloco_nao_aninha():
    r = tokenizar("/* a /* b */ c */")
    assert [t["lexema"] for t in r["tokens"]] == ["c", "*", "/"]


def test_barra_asterisco_barra_nao_fecha_comentario_recem_aberto():
    r = tokenizar("/*/ resto")
    assert len(r["erros"]) == 1 and "não fechado" in r["erros"][0]["mensagem"]


def test_comentario_de_bloco_nao_fechado():
    r = tokenizar("int a;\n/* abre e nunca fecha\nint b;")
    assert [t["lexema"] for t in r["tokens"]] == ["int", "a", ";"]
    erro = r["erros"][0]
    assert (erro["linha"], erro["coluna"]) == (2, 1)
    assert "Comentário de bloco não fechado" in erro["mensagem"]
    assert r["sucesso"] is False


def test_espacos_tabs_e_quebras_nao_geram_tokens():
    assert tokenizar(" \t\n\r\n\f\v  \n")["tokens"] == []


def test_espacos_entre_tokens_sao_ignorados_mas_a_posicao_conta():
    r = tokenizar("a\t=   1")
    assert [(t["lexema"], t["coluna"]) for t in r["tokens"]] == [("a", 1), ("=", 3), ("1", 7)]


# ---------------- Posições ----------------
def test_linhas_e_colunas_do_exemplo_da_especificacao():
    r = tokenizar("int numero = 10;")
    assert [(t["tipo"], t["lexema"], t["linha"], t["coluna"]) for t in r["tokens"]] == [
        ("PALAVRA_RESERVADA", "int", 1, 1),
        ("IDENTIFICADOR", "numero", 1, 5),
        ("OPERADOR_ATRIBUICAO", "=", 1, 12),
        ("LITERAL_INTEIRO", "10", 1, 14),
        ("DELIMITADOR", ";", 1, 16),
    ]


def test_posicoes_em_varias_linhas():
    r = tokenizar("int a;\n  int b;\n\nreturn 0;")
    pos = [(t["lexema"], t["linha"], t["coluna"]) for t in r["tokens"]]
    assert ("a", 1, 5) in pos and ("int", 2, 3) in pos and ("b", 2, 7) in pos
    assert ("return", 4, 1) in pos and ("0", 4, 8) in pos


@pytest.mark.parametrize("quebra", ["\n", "\r\n", "\r"])
def test_todos_os_estilos_de_quebra_de_linha_contam_uma_linha(quebra):
    r = tokenizar(f"a{quebra}b{quebra}c")
    assert [(t["lexema"], t["linha"], t["coluna"]) for t in r["tokens"]] == [("a", 1, 1), ("b", 2, 1), ("c", 3, 1)]


def test_tab_conta_como_uma_coluna():
    assert tokenizar("\tx")["tokens"][0]["coluna"] == 2


def test_colunas_contam_caracteres_e_nao_bytes_nem_utf16():
    r = tokenizar('"😀" x')
    x = r["tokens"][-1]
    assert x["lexema"] == "x" and x["coluna"] == 5


def test_inicio_e_fim_em_utf16_recuperam_o_lexema_mesmo_com_emoji():
    codigo = 's = "😀😀"; @ int // ✓ fim'
    r = tokenizar(codigo)
    for item in r["tokens"] + r["erros"] + r["comentarios"]:
        assert fatia(codigo, item) == item["lexema"]


# ---------------- Erros léxicos ----------------
@pytest.mark.parametrize("c", list("@#$`~^?:\\"))
def test_caracteres_nao_reconhecidos(c):
    r = tokenizar(f"a {c} b")
    assert [e["lexema"] for e in r["erros"]] == [c]
    erro = r["erros"][0]
    assert (erro["linha"], erro["coluna"]) == (1, 3)
    assert erro["tipo"] == "ERRO_LEXICO"
    assert f"'{c}'" in erro["mensagem"]
    assert [t["lexema"] for t in r["tokens"]] == ["a", "b"]  # continua depois do erro


def test_hash_tem_dica_sobre_preprocessador():
    assert "pré-processador" in tokenizar("#include <stdio.h>")["erros"][0]["dica"]


def test_espaco_especial_nbsp_e_reportado_com_dica_didatica():
    r = tokenizar("int\u00a0x;")
    assert len(r["erros"]) == 1
    assert "U+00A0" in r["erros"][0]["mensagem"]
    assert "espaço comum" in r["erros"][0]["dica"]


def test_caractere_de_controle_nao_quebra_e_e_mostrado_como_codigo():
    r = tokenizar("a\x00b")
    assert "U+0000" in r["erros"][0]["mensagem"]


def test_varios_erros_sao_acumulados_na_mesma_analise():
    r = tokenizar("int a = @;\nint b = #;\nint c = 3.;")
    assert [(e["lexema"], e["linha"]) for e in r["erros"]] == [("@", 1), ("#", 2), ("3.", 3)]
    assert r["sucesso"] is False
    assert r["resumo"]["total_erros"] == 3


def test_programa_com_erros_sintaticos_mas_tokens_validos_e_tokenizado_normalmente():
    r = tokenizar("int x = 10\nint y = x + ;\nz = 5;")
    assert r["sucesso"] is True and r["erros"] == []
    assert r["resumo"]["total_tokens"] == 14


# ---------------- Casos de borda ----------------
def test_codigo_vazio():
    r = tokenizar("")
    assert r["tokens"] == [] and r["erros"] == [] and r["sucesso"] is True
    assert r["resumo"]["total_tokens"] == 0


def test_somente_espacos():
    r = tokenizar("    \n\n\t ")
    assert r["tokens"] == [] and r["erros"] == [] and r["sucesso"] is True


def test_somente_comentarios():
    r = tokenizar("// um\n/* dois */\n// tres")
    assert r["tokens"] == [] and len(r["comentarios"]) == 3 and r["sucesso"] is True


def test_token_no_fim_do_arquivo_sem_quebra_de_linha():
    for codigo, esperado in [("x", "x"), ("12", "12"), ("a;", ";"), ("a<=", "<="), ("a==", "==")]:
        assert lexemas(codigo)[-1] == esperado


def test_comentario_de_linha_no_fim_sem_quebra():
    r = tokenizar("a // fim")
    assert lexemas("a // fim") == ["a"] and len(r["comentarios"]) == 1


def test_entrada_grande_roda_rapido():
    import time
    codigo = "int a = 1;\n" * 1800  # ~19,8 mil caracteres
    inicio = time.perf_counter()
    r = tokenizar(codigo)
    assert time.perf_counter() - inicio < 2.0
    assert r["resumo"]["total_tokens"] == 1800 * 5


# ---------------- Resumo e caminho ----------------
def test_resumo_por_categoria_na_ordem_canonica_e_sem_zeros():
    r = tokenizar("int a = 1 + 2.5; // c")
    resumo = r["resumo"]
    assert list(resumo["por_categoria"]) == [c for c in CATEGORIAS if c in resumo["por_categoria"]]
    assert resumo["por_categoria"] == {
        "PALAVRA_RESERVADA": 1, "IDENTIFICADOR": 1, "LITERAL_INTEIRO": 1, "LITERAL_REAL": 1,
        "OPERADOR_ARITMETICO": 1, "OPERADOR_ATRIBUICAO": 1, "DELIMITADOR": 1,
    }
    assert resumo["total_tokens"] == 7 and resumo["total_comentarios"] == 1
    assert sum(resumo["por_categoria"].values()) == resumo["total_tokens"]


def test_caminho_do_automato_tem_um_passo_por_caractere():
    codigo = 'int numero = 3.14 <= "oi" + \'x\';'
    for tk in tokenizar(codigo)["tokens"]:
        assert "".join(p["c"] for p in tk["caminho"]) == tk["lexema"]


def test_caminho_do_identificador_e_do_real():
    r = tokenizar("ab 12.5")
    assert [p["estado"] for p in r["tokens"][0]["caminho"]] == ["IDENT", "IDENT"]
    assert [p["estado"] for p in r["tokens"][1]["caminho"]] == ["INT", "INT", "REAL_PONTO", "REAL"]
    assert [p["classe"] for p in r["tokens"][1]["caminho"]] == ["digito", "digito", "ponto", "digito"]


def test_caminho_do_operador_composto():
    tk = tokenizar("<=")["tokens"][0]
    assert [p["estado"] for p in tk["caminho"]] == ["MENOR", "MENOR_IGUAL"]


def test_erro_termina_no_estado_erro():
    erro = tokenizar("3.")["erros"][0]
    assert erro["caminho"][-1]["estado"] == "ERRO"
    assert tokenizar("@")["erros"][0]["caminho"] == [{"c": "@", "classe": "simbolo", "estado": "ERRO"}]


def test_lexema_muito_longo_e_truncado_na_exibicao_mas_nao_nas_posicoes():
    codigo = "a" * 100
    tk = tokenizar(codigo)["tokens"][0]
    assert tk["lexema"].endswith("…") and len(tk["lexema"]) == 40
    assert (tk["inicio"], tk["fim"]) == (0, 100)


def test_todo_caractere_nao_branco_pertence_a_um_token_erro_ou_comentario():
    codigo = (
        "int a = 10; // c\nfloat b = 2.5; /* x */ char c = 'z';\n"
        'if (a >= b && !c) { return "ok"; } @ 3. "aberta\n'
    )
    r = tokenizar(codigo)
    cobertos = set()
    for item in r["tokens"] + r["erros"] + r["comentarios"]:
        cobertos.update(range(item["inicio"], item["fim"]))
    for pos, ch in enumerate(codigo):
        if not ch.isspace():
            assert pos in cobertos, (pos, ch)
