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
    assert corpo["recebido"] is True
    assert corpo["mensagem"] == "Código recebido com sucesso."
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


def test_codigo_com_erros_intencionais_e_recebido():
    r = client.post("/api/analisar", json={"codigo": "int x = 10\nint y = x + ;"})
    assert r.status_code == 200 and r.json()["recebido"] is True


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
