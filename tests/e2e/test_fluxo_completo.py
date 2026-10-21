"""Testes de ponta a ponta (navegador real) contra a aplicação em execução.

Pré-requisitos:
    pip install -r tests/e2e/requirements.txt
    playwright install chromium
    docker compose up --build -d

Execução:
    pytest tests/e2e -v
    BASE_URL=http://localhost:8080 pytest tests/e2e -v   # (padrão)
"""
import json
import os

import pytest
from playwright.sync_api import expect, sync_playwright

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080")


@pytest.fixture(scope="session")
def navegador():
    with sync_playwright() as p:
        nav = p.chromium.launch()
        yield nav
        nav.close()


@pytest.fixture()
def pagina(navegador):
    contexto = navegador.new_context(viewport={"width": 1280, "height": 900})
    pg = contexto.new_page()
    pg.goto(BASE_URL)
    # Aguarda os exemplos serem carregados do backend
    expect(pg.locator("#seletor-exemplos option")).not_to_have_count(1)
    yield pg
    contexto.close()


def contar_analises(pg):
    registro = []
    pg.on("request", lambda r: registro.append(r) if r.url.endswith("/api/analisar") else None)
    return registro


# ---------- Tela ----------
def test_tela_identifica_sistema_e_linguagem(pagina):
    expect(pagina.locator("#titulo-sistema")).to_contain_text("Analisador Educacional")
    expect(pagina.locator("#linguagem-analisada")).to_have_text("C")


def test_area_de_entrada_usa_fonte_monoespacada(pagina):
    familia = pagina.eval_on_selector("#entrada-codigo", "e => getComputedStyle(e).fontFamily")
    assert "mono" in familia.lower() or "consolas" in familia.lower() or "menlo" in familia.lower()
    altura = pagina.eval_on_selector("#entrada-codigo", "e => e.getBoundingClientRect().height")
    assert altura >= 200


def test_elementos_obrigatorios_visiveis(pagina):
    for seletor in ["#entrada-codigo", "#btn-analisar", "#resultado", "#seletor-exemplos"]:
        expect(pagina.locator(seletor)).to_be_visible()


# ---------- Fluxo principal ----------
def test_fluxo_completo_exemplo_edicao_e_analise(pagina):
    pagina.select_option("#seletor-exemplos", index=3)  # 3º exemplo (if)
    codigo = pagina.input_value("#entrada-codigo")
    assert "if" in codigo
    pagina.fill("#entrada-codigo", codigo + "int extra = 1;\n")  # edita
    pagina.click("#btn-analisar")
    resultado = pagina.locator("#resultado")
    expect(resultado).to_contain_text("Código recebido com sucesso.")
    expect(resultado).to_contain_text("próximas etapas")
    assert "int extra = 1;" in pagina.input_value("#entrada-codigo")  # código preservado


def test_cada_exemplo_carrega_e_pode_ser_analisado(pagina):
    total = pagina.locator("#seletor-exemplos option").count() - 1
    assert total >= 3
    anterior = None
    for i in range(1, total + 1):
        pagina.select_option("#seletor-exemplos", index=i)
        atual = pagina.input_value("#entrada-codigo")
        assert atual.strip() and atual != anterior  # substitui o conteúdo anterior
        anterior = atual
        pagina.click("#btn-analisar")
        expect(pagina.locator("#resultado")).to_contain_text("Código recebido com sucesso.")


def test_caracteres_especiais_chegam_ao_backend(pagina):
    texto = 'x = "ação ✓ 😀"; // <b>&amp;</b>'
    pagina.fill("#entrada-codigo", texto)
    pagina.click("#btn-analisar")
    expect(pagina.locator("#resultado")).to_contain_text(f"{len(texto)} caracteres")


# ---------- Validações ----------
def test_entrada_vazia_nao_envia_requisicao(pagina):
    envios = contar_analises(pagina)
    pagina.fill("#entrada-codigo", "")
    pagina.click("#btn-analisar")
    expect(pagina.locator("#resultado")).to_contain_text(
        "Informe um código-fonte antes de solicitar a análise."
    )
    assert envios == []


def test_entrada_so_com_espacos(pagina):
    envios = contar_analises(pagina)
    pagina.fill("#entrada-codigo", "   \n\t  ")
    pagina.click("#btn-analisar")
    expect(pagina.locator("#resultado")).to_contain_text("apenas espaços em branco")
    assert envios == []


# ---------- Falhas ----------
def test_falha_de_comunicacao(pagina):
    pagina.route("**/api/analisar", lambda r: r.abort())
    pagina.fill("#entrada-codigo", "int a;")
    pagina.click("#btn-analisar")
    expect(pagina.locator("#resultado")).to_contain_text(
        "Não foi possível comunicar com o servidor. Verifique a conexão e tente novamente."
    )
    expect(pagina.locator("#btn-analisar")).to_be_enabled()
    assert pagina.input_value("#entrada-codigo") == "int a;"


def test_erro_interno_mostra_mensagem_generica(pagina):
    pagina.route(
        "**/api/analisar",
        lambda r: r.fulfill(
            status=500,
            content_type="application/json",
            body=json.dumps({"erro": "erro_interno", "mensagem": "Traceback /app/main.py"}),
        ),
    )
    pagina.fill("#entrada-codigo", "int a;")
    pagina.click("#btn-analisar")
    expect(pagina.locator("#resultado")).to_contain_text("Ocorreu um erro inesperado")
    expect(pagina.locator("#resultado")).not_to_contain_text("Traceback")


def test_recupera_apos_falha(pagina):
    pagina.route("**/api/analisar", lambda r: r.abort())
    pagina.fill("#entrada-codigo", "int a;")
    pagina.click("#btn-analisar")
    expect(pagina.locator("#resultado")).to_contain_text("Falha de comunicação")
    pagina.unroute("**/api/analisar")
    pagina.click("#btn-analisar")
    expect(pagina.locator("#resultado")).to_contain_text("Código recebido com sucesso.")


# ---------- Backend acessado diretamente (sem confiar no frontend) ----------
def test_backend_valida_mesmo_sem_frontend(pagina):
    r = pagina.request.post(f"{BASE_URL}/api/analisar", data={})
    assert r.status == 400 and r.json()["erro"] == "requisicao_invalida"
    r = pagina.request.post(f"{BASE_URL}/api/analisar", data={"codigo": ""})
    assert r.status == 400 and r.json()["erro"] == "codigo_vazio"


def test_regressao_etapa_1_hello_world(pagina):
    r = pagina.request.get(f"{BASE_URL}/api/hello")
    assert r.status == 200 and r.json() == {"message": "Hello, World!"}
    assert pagina.request.get(f"{BASE_URL}/api/health").json() == {"status": "ok"}
