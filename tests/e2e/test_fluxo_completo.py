"""Testes de ponta a ponta (navegador real) contra a aplicação em execução (Etapas 2 e 3).

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
    expect(resultado).to_contain_text("Análise léxica concluída")  # Etapa 3 (antes: "Código recebido com sucesso.")
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
        expect(pagina.locator("#resultado")).to_contain_text("Análise léxica concluída")


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
    expect(pagina.locator("#resultado")).to_contain_text("Análise léxica concluída")


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


# =====================================================================
# Etapa 3: análise léxica
# =====================================================================
def analisar_exemplo(pg, indice):
    pg.select_option("#seletor-exemplos", index=indice)
    pg.click("#btn-analisar")
    expect(pg.locator("#painel-lexico")).to_be_visible()


def test_tabela_de_tokens_com_codigo_simples(pagina):
    pagina.fill("#entrada-codigo", "int numero = 10;")
    pagina.click("#btn-analisar")
    linhas = pagina.locator("#tabela-tokens-corpo tr")
    expect(linhas).to_have_count(5)
    expect(linhas.nth(0)).to_contain_text("PALAVRA_RESERVADA")
    expect(linhas.nth(0)).to_contain_text("int")
    expect(linhas.nth(3)).to_contain_text("LITERAL_INTEIRO")
    expect(pagina.locator("#resultado")).to_contain_text("5 tokens, nenhum erro léxico")
    expect(pagina.locator("#resumo-lexico")).to_contain_text("5 tokens")


def test_exemplo_de_operadores_reconhece_maior_casamento(pagina):
    analisar_exemplo(pagina, 7)  # exemplo 7
    tabela = pagina.locator("#tabela-tokens-corpo")
    expect(tabela).to_contain_text("<=")
    expect(tabela).to_contain_text("&&")
    expect(tabela).to_contain_text("!=")
    expect(pagina.locator("#erros-lexicos")).to_contain_text("Nenhum erro léxico")


def test_exemplo_com_erros_lexicos_mostra_mensagens_claras(pagina):
    analisar_exemplo(pagina, 8)  # exemplo 8
    erros = pagina.locator("#erros-lexicos .erro-item")
    expect(erros).to_have_count(8)
    expect(erros.nth(0)).to_contain_text("Erro léxico na linha 2, coluna 19")
    expect(erros.nth(0)).to_contain_text("caractere não reconhecido: '@'")
    expect(pagina.locator("#resultado")).to_contain_text("8 erros léxicos")
    expect(pagina.locator("#codigo-colorido .tk-erro")).to_have_count(8)
    expect(pagina.locator("#resultado")).not_to_contain_text("Traceback")
    # a aplicação continua utilizável: dá para analisar outro código
    pagina.fill("#entrada-codigo", "int ok = 1;")
    pagina.click("#btn-analisar")
    expect(pagina.locator("#erros-lexicos")).to_contain_text("Nenhum erro léxico")


def test_codigo_com_erros_sintaticos_e_tokenizado_normalmente(pagina):
    analisar_exemplo(pagina, 5)  # erros sintáticos/semânticos, tokens válidos
    expect(pagina.locator("#resultado")).to_contain_text("nenhum erro léxico")
    expect(pagina.locator("#tabela-tokens-corpo tr")).to_have_count(14)


def test_codigo_colorido_usa_cores_diferentes_por_categoria(pagina):
    analisar_exemplo(pagina, 6)
    cores = pagina.eval_on_selector_all(
        "#codigo-colorido .tk",
        "els => [...new Set(els.map(e => getComputedStyle(e).backgroundColor))].length",
    )
    assert cores >= 6
    assert pagina.inner_text("#codigo-colorido").strip().startswith("int idade")


def test_passo_a_passo_navega_e_mostra_estados_do_automato(pagina):
    pagina.fill("#entrada-codigo", "int a = 1;")
    pagina.click("#btn-analisar")
    expect(pagina.locator("#passos-info")).to_contain_text("Passo 0 de")
    pagina.click("#passo-proximo")
    expect(pagina.locator("#passos-narracao")).to_contain_text("Lendo 'i'")
    expect(pagina.locator("#passos-transicoes .trans")).to_have_count(1)
    pagina.click("#passo-token-proximo")
    expect(pagina.locator("#passos-narracao")).to_contain_text("token é emitido: <RESERV, int>")
    pagina.click("#passo-fim")
    expect(pagina.locator("#passos-narracao")).to_contain_text("Fim da entrada")
    expect(pagina.locator("#passo-proximo")).to_be_disabled()
    pagina.click("#passo-inicio")
    expect(pagina.locator("#passos-info")).to_contain_text("Passo 0 de")


def test_passo_a_passo_reproducao_automatica_chega_ao_fim(pagina):
    pagina.fill("#entrada-codigo", "int a;")
    pagina.click("#btn-analisar")
    pagina.select_option("#passo-velocidade", "rapida")
    pagina.click("#passo-reproduzir")
    expect(pagina.locator("#passos-narracao")).to_contain_text("Fim da entrada", timeout=8000)
    expect(pagina.locator("#passo-reproduzir")).to_have_text("▶ Reproduzir")


def test_tutorial_existe_e_abre(pagina):
    expect(pagina.locator("#tutorial")).to_be_visible()
    pagina.click("#tutorial > summary")
    expect(pagina.locator("#tutorial")).to_have_attribute("open", "")
    expect(pagina.locator("#tutorial svg")).to_have_count(2)
    expect(pagina.locator("#legenda-categorias tbody tr")).to_have_count(11)


def test_codigo_vazio_continua_barrado_na_etapa_3(pagina):
    pagina.fill("#entrada-codigo", "")
    pagina.click("#btn-analisar")
    expect(pagina.locator("#resultado")).to_contain_text("Informe um código-fonte")
    expect(pagina.locator("#painel-lexico")).to_be_hidden()


def test_falha_de_comunicacao_esconde_resultados_antigos(pagina):
    analisar_exemplo(pagina, 1)
    pagina.route("**/api/analisar", lambda r: r.abort())
    pagina.click("#btn-analisar")
    expect(pagina.locator("#resultado")).to_contain_text("Falha de comunicação")
    expect(pagina.locator("#painel-lexico")).to_be_hidden()


def test_endpoint_devolve_contrato_lexico_completo(pagina):
    r = pagina.request.post(f"{BASE_URL}/api/analisar", data={"codigo": "int x = 1; @"})
    assert r.status == 200
    corpo = r.json()
    assert corpo["recebido"] is True and corpo["sucesso"] is False
    assert corpo["erros"][0]["tipo"] == "ERRO_LEXICO" and corpo["erros"][0]["lexema"] == "@"
    assert corpo["tokens"][0]["tipo"] == "PALAVRA_RESERVADA"
    assert corpo["resumo"]["total_tokens"] == 5 and corpo["resumo"]["total_erros"] == 1


# ---------- Celular ----------
def test_layout_de_celular_sem_rolagem_horizontal(navegador):
    contexto = navegador.new_context(
        viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True
    )
    pg = contexto.new_page()
    pg.goto(BASE_URL)
    expect(pg.locator("#seletor-exemplos option")).not_to_have_count(1)
    pg.select_option("#seletor-exemplos", index=8)
    pg.click("#btn-analisar")
    expect(pg.locator("#painel-lexico")).to_be_visible()
    largura = pg.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]")
    assert largura[0] <= largura[1], f"rolagem horizontal na página: {largura}"
    # botões de controle com área de toque confortável
    altura = pg.eval_on_selector("#passo-proximo", "e => e.getBoundingClientRect().height")
    assert altura >= 40
    contexto.close()
