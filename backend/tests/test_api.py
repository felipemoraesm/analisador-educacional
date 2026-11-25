import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


# ---------- Regressão da Etapa 1 ----------
def test_hello_continua_funcionando():
    r = client.get("/api/hello")
    assert r.status_code == 200
    assert r.json() == {"message": "Hello, World!"}


def test_health_continua_funcionando():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------- POST /api/analisar: requisições válidas ----------
def test_codigo_valido():
    r = client.post("/api/analisar", json={"codigo": "int numero = 10;"})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["recebido"] is True  # campo mantido da Etapa 2
    assert corpo["sucesso"] is True
    # Etapa 3: a mensagem passou a descrever a análise léxica (alteração intencional,
    # documentada em docs/testes.md); antes era "Código recebido com sucesso."
    assert corpo["mensagem"] == "Análise léxica concluída: 5 tokens, nenhum erro léxico."
    assert corpo["linhas"] == 1
    assert corpo["caracteres"] == len("int numero = 10;")


def test_contagem_de_linhas():
    r = client.post("/api/analisar", json={"codigo": "int a;\nint b;\nint c;\n"})
    assert r.json()["linhas"] == 3


def test_caracteres_especiais_e_unicode():
    codigo = 'printf("%d\\n", x); // ação ✓ \u00e9 \U0001F600 <script>alert(1)</script>'
    r = client.post("/api/analisar", json={"codigo": codigo})
    assert r.status_code == 200
    assert r.json()["caracteres"] == len(codigo)


def test_codigo_com_erros_sintaticos_e_tokenizado_normalmente():
    r = client.post("/api/analisar", json={"codigo": "int x = 10\nint y = x + ;"})
    corpo = r.json()
    assert r.status_code == 200 and corpo["recebido"] is True
    assert corpo["sucesso"] is True and corpo["erros"] == []
    assert corpo["resumo"]["total_tokens"] == 10


# ---------- Validações de entrada ----------
def test_codigo_vazio():
    r = client.post("/api/analisar", json={"codigo": ""})
    assert r.status_code == 400
    assert r.json() == {
        "recebido": False,
        "erro": "codigo_vazio",
        "mensagem": "Informe um código-fonte antes de solicitar a análise.",
    }


@pytest.mark.parametrize("texto", ["   ", "\n\n", "\t \n"])
def test_codigo_somente_espacos(texto):
    r = client.post("/api/analisar", json={"codigo": texto})
    assert r.status_code == 400
    assert r.json()["erro"] == "codigo_somente_espacos"


def test_codigo_muito_grande():
    r = client.post("/api/analisar", json={"codigo": "x" * 20_001})
    assert r.status_code == 413
    assert r.json()["erro"] == "codigo_muito_grande"


# ---------- Requisições inválidas ----------
@pytest.mark.parametrize(
    "corpo",
    [
        {},
        {"outro": "int x;"},
        {"codigo": None},
        {"codigo": 123},
        {"codigo": ["int x;"]},
        {"codigo": {"a": 1}},
        [],
        "texto solto",
    ],
)
def test_corpo_invalido(corpo):
    r = client.post("/api/analisar", json=corpo)
    assert r.status_code == 400
    assert r.json()["erro"] == "requisicao_invalida"
    assert r.json()["recebido"] is False


def test_json_malformado():
    r = client.post(
        "/api/analisar", content="{codigo: int x", headers={"Content-Type": "application/json"}
    )
    assert r.status_code == 400
    assert r.json()["erro"] == "requisicao_invalida"


def test_corpo_ausente():
    r = client.post("/api/analisar")
    assert r.status_code == 400


def test_resposta_de_erro_nao_expoe_detalhes_internos():
    r = client.post("/api/analisar", json={"codigo": 123})
    texto = r.text.lower()
    for proibido in ("traceback", "pydantic", "loc", "/app/", "input_value", "type_error"):
        assert proibido not in texto


def test_metodo_nao_permitido():
    r = client.get("/api/analisar")
    assert r.status_code == 405
    assert r.json()["recebido"] is False


def test_rota_inexistente():
    r = client.get("/api/nao-existe")
    assert r.status_code == 404
    assert r.json()["erro"] == "nao_encontrado"


# ---------- Erro inesperado ----------
def test_erro_inesperado_retorna_mensagem_generica(monkeypatch):
    def quebra(_):
        raise RuntimeError("segredo interno /home/usuario/chave")

    monkeypatch.setattr("app.main.validar_codigo", quebra)
    r = client.post("/api/analisar", json={"codigo": "int x;"})
    assert r.status_code == 500
    assert r.json()["erro"] == "erro_interno"
    assert "segredo" not in r.text and "/home" not in r.text


# ---------- GET /api/exemplos ----------
def test_exemplos_formato_e_quantidade():
    r = client.get("/api/exemplos")
    assert r.status_code == 200
    exemplos = r.json()["exemplos"]
    assert len(exemplos) >= 3
    ids = [e["id"] for e in exemplos]
    assert len(ids) == len(set(ids))
    for e in exemplos:
        assert set(e) == {"id", "titulo", "descricao", "codigo"}
        assert all(isinstance(v, str) and v.strip() for v in e.values())


def test_todo_exemplo_e_aceito_pelo_endpoint_de_analise():
    for e in client.get("/api/exemplos").json()["exemplos"]:
        r = client.post("/api/analisar", json={"codigo": e["codigo"]})
        assert r.status_code == 200, e["id"]


# ---------- Etapa 3: contrato da análise léxica ----------
def test_resposta_lexica_segue_o_contrato():
    corpo = client.post("/api/analisar", json={"codigo": "int numero = 10; // fim"}).json()
    # Etapa 4: acrescentados "lexico" e "sintatico" (aditivo); todos os campos da Etapa 3 permanecem
    etapa3 = {"recebido", "sucesso", "mensagem", "linhas", "caracteres", "tokens", "erros", "comentarios", "resumo"}
    assert set(corpo) == etapa3 | {"lexico", "sintatico"}
    assert corpo["tokens"][0] == {
        "tipo": "PALAVRA_RESERVADA", "lexema": "int", "linha": 1, "coluna": 1,
        "fim_linha": 1, "fim_coluna": 4,  # Etapa 4: campos acrescentados (aditivo)
        "inicio": 0, "fim": 3,
        "caminho": [
            {"c": "i", "classe": "letra", "estado": "IDENT"},
            {"c": "n", "classe": "letra", "estado": "IDENT"},
            {"c": "t", "classe": "letra", "estado": "IDENT"},
        ],
    }
    assert corpo["comentarios"][0]["tipo"] == "COMENTARIO_LINHA"
    assert set(corpo["resumo"]) == {"total_tokens", "total_erros", "total_comentarios", "por_categoria"}


def test_erro_lexico_retorna_200_com_sucesso_false_e_erros():
    r = client.post("/api/analisar", json={"codigo": "int a;\nint b = @;"})
    assert r.status_code == 200  # a análise foi feita; erros léxicos são resultado, não requisição inválida
    corpo = r.json()
    assert corpo["recebido"] is True and corpo["sucesso"] is False
    assert corpo["mensagem"] == "Análise léxica concluída: 7 tokens e 1 erro léxico."
    erro = corpo["erros"][0]
    assert erro["tipo"] == "ERRO_LEXICO" and erro["lexema"] == "@"
    assert (erro["linha"], erro["coluna"]) == (2, 9)
    assert erro["mensagem"] == "Caractere não reconhecido: '@'"
    assert {"dica", "inicio", "fim", "caminho"} <= set(erro)
    assert [t["lexema"] for t in corpo["tokens"]][-2:] == ["=", ";"]  # continua após o erro


def test_varios_erros_lexicos_na_mesma_resposta():
    corpo = client.post("/api/analisar", json={"codigo": "@ # $"}).json()
    assert [e["lexema"] for e in corpo["erros"]] == ["@", "#", "$"]
    assert corpo["mensagem"] == "Análise léxica concluída: 0 tokens e 3 erros léxicos."


def test_somente_comentarios_e_sucesso_sem_tokens():
    corpo = client.post("/api/analisar", json={"codigo": "// so comentario"}).json()
    assert corpo["sucesso"] is True and corpo["tokens"] == []
    assert corpo["resumo"]["total_comentarios"] == 1


def test_endpoint_com_unicode_e_emoji_devolve_posicoes_utf16():
    codigo = 'x = "😀"; y'
    corpo = client.post("/api/analisar", json={"codigo": codigo}).json()
    y = corpo["tokens"][-1]
    assert y["lexema"] == "y" and (y["inicio"], y["fim"]) == (10, 11)  # 😀 ocupa 2 unidades UTF-16


def test_erro_do_scanner_nao_vaza_detalhes(monkeypatch):
    def quebra(_):
        raise RuntimeError("detalhe interno /srv/segredo")

    monkeypatch.setattr("app.main.tokenizar", quebra)
    r = client.post("/api/analisar", json={"codigo": "int a;"})
    assert r.status_code == 500 and r.json()["erro"] == "erro_interno"
    assert "segredo" not in r.text


def test_validacao_da_etapa_2_continua_antes_do_scanner(monkeypatch):
    chamadas = []
    monkeypatch.setattr("app.main.tokenizar", lambda c: chamadas.append(c))
    assert client.post("/api/analisar", json={"codigo": ""}).status_code == 400
    assert client.post("/api/analisar", json={"codigo": "  \n"}).status_code == 400
    assert client.post("/api/analisar", json={}).status_code == 400
    assert chamadas == []  # o scanner nem é chamado para entradas inválidas


def test_exemplos_lexicos_tem_o_resultado_esperado():
    por_id = {e["id"]: e["codigo"] for e in client.get("/api/exemplos").json()["exemplos"]}
    ok = client.post("/api/analisar", json={"codigo": por_id["operadores"]}).json()
    assert ok["sucesso"] is True and ok["resumo"]["por_categoria"]["OPERADOR_RELACIONAL"] >= 3
    ruim = client.post("/api/analisar", json={"codigo": por_id["erros_lexicos"]}).json()
    assert ruim["sucesso"] is False and len(ruim["erros"]) == 8


def test_surrogate_isolado_retorna_400_e_nao_500():
    r = client.post("/api/analisar", content=b'{"codigo": "int a; \\ud800"}',
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 400
    assert r.json()["erro"] == "codigo_invalido"


# ---------- Etapa 4: análise sintática no endpoint ----------
def _analisar(codigo):
    r = client.post("/api/analisar", json={"codigo": codigo})
    assert r.status_code == 200
    return r.json()


def test_codigo_valido_retorna_tokens_ast_e_sucesso():
    corpo = _analisar("int resultado = 10 + 5 * 2;")
    assert corpo["lexico"]["sucesso"] is True and len(corpo["lexico"]["tokens"]) == 9
    sint = corpo["sintatico"]
    assert sint["executado"] is True and sint["sucesso"] is True and sint["erros"] == []
    assert sint["ast"]["tipo"] == "PROGRAMA" and sint["motivo"] is None
    assert sint["mensagem"] == "Análise sintática concluída: programa válido (AST com 7 nós)."
    assert sint["resumo"]["total_nos"] == 7 and "ADICAO" in sint["regras"]


def test_campos_da_etapa_3_foram_preservados_e_coincidem_com_lexico():
    corpo = _analisar("int a = 1; @")
    for campo in ("sucesso", "tokens", "erros", "comentarios", "resumo"):
        assert corpo[campo] == corpo["lexico"][campo], campo
    assert corpo["recebido"] is True and corpo["mensagem"].startswith("Análise léxica concluída")


def test_erro_sintatico_retorna_erros_e_ast_nula():
    corpo = _analisar("int numero = 10}")
    assert corpo["lexico"]["sucesso"] is True  # os tokens são válidos
    sint = corpo["sintatico"]
    assert sint["executado"] is True and sint["sucesso"] is False and sint["ast"] is None
    assert sint["erros"] == [{
        "tipo": "ERRO_SINTATICO", "linha": 1, "coluna": 16, "inicio": 15, "fim": 16,
        "encontrado": "}", "encontrado_tipo": "DELIMITADOR", "esperado": [";"],
        "mensagem": "Era esperado ';' ao final da declaração, mas foi encontrado '}'.",
        "regra": 'declaracao = tipo IDENTIFICADOR [ "=" expressao ] ";" ;', "dica": None,
    }]
    assert corpo["sucesso"] is True  # "sucesso" de nível superior continua sendo o léxico (compatibilidade)


def test_erro_lexico_nao_executa_o_parser(monkeypatch):
    chamadas = []
    monkeypatch.setattr("app.analise.analisar_sintaxe", lambda *a: chamadas.append(a))
    corpo = _analisar("int a = @;")
    assert chamadas == []  # decisão de projeto: sem parser quando há erro léxico
    sint = corpo["sintatico"]
    assert sint["executado"] is False and sint["sucesso"] is None and sint["ast"] is None
    assert "erros léxicos" in sint["motivo"] and sint["erros"] == []
    assert corpo["sucesso"] is False and corpo["erros"][0]["lexema"] == "@"  # erros léxicos continuam aparecendo


def test_codigo_vazio_continua_sendo_400_como_na_etapa_2():
    assert client.post("/api/analisar", json={"codigo": ""}).status_code == 400
    assert client.post("/api/analisar", json={"codigo": "   "}).status_code == 400


def test_somente_comentarios_gera_programa_vazio():
    sint = _analisar("// nada")["sintatico"]
    assert sint["sucesso"] is True and sint["ast"]["filhos"] == [] and "programa vazio" in sint["mensagem"]


def test_falha_inesperada_do_parser_retorna_500_generico(monkeypatch):
    def quebra(*_):
        raise RuntimeError("detalhe /srv/segredo")

    monkeypatch.setattr("app.analise.analisar_sintaxe", quebra)
    r = client.post("/api/analisar", json={"codigo": "int a;"})
    assert r.status_code == 500 and "segredo" not in r.text


def test_ast_profunda_dentro_do_limite_e_serializada_sem_erro():
    corpo = _analisar("x = " + " + ".join(["1"] * 100) + ";")
    assert corpo["sintatico"]["sucesso"] is True


def test_ast_acima_da_altura_maxima_vira_erro_claro_e_nao_500():
    corpo = _analisar("x = " + " + ".join(["1"] * 400) + ";")
    assert corpo["sintatico"]["sucesso"] is False
    assert "profunda demais" in corpo["sintatico"]["erros"][0]["mensagem"]


def test_entrada_no_limite_de_tamanho_e_processada_rapido():
    import time
    codigo = "int a = 1;\n" * 1800
    inicio = time.perf_counter()
    corpo = _analisar(codigo)
    assert time.perf_counter() - inicio < 5
    assert corpo["sintatico"]["sucesso"] is True and corpo["sintatico"]["texto"] is None


def test_exemplos_da_etapa_4_tem_o_resultado_esperado():
    por_id = {e["id"]: e["codigo"] for e in client.get("/api/exemplos").json()["exemplos"]}
    for id_ in ("declaracao", "aritmetica", "condicional", "if_else", "literais", "operadores",
                "precedencia", "funcoes", "aninhamento"):
        assert _analisar(por_id[id_])["sintatico"]["sucesso"] is True, id_
    assert len(_analisar(por_id["erro_intencional"])["sintatico"]["erros"]) == 2
    assert len(_analisar(por_id["erros_sintaticos"])["sintatico"]["erros"]) == 6
    lexico_ruim = _analisar(por_id["erros_lexicos"])
    assert lexico_ruim["sintatico"]["executado"] is False


def test_resposta_do_endpoint_e_json_valido_com_utf8():
    r = client.post("/api/analisar", json={"codigo": 'char s = "ação ✓ 😀";'})
    assert r.status_code == 200 and r.json()["sintatico"]["sucesso"] is True


def test_regressao_scanner_endpoint_etapa_3_tokens_inalterados():
    corpo = _analisar("int numero = 10;")
    assert [(t["tipo"], t["lexema"]) for t in corpo["tokens"]] == [
        ("PALAVRA_RESERVADA", "int"), ("IDENTIFICADOR", "numero"), ("OPERADOR_ATRIBUICAO", "="),
        ("LITERAL_INTEIRO", "10"), ("DELIMITADOR", ";")]
