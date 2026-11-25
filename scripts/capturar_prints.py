"""Gera os prints da interface em docs/img/ (requer a aplicação em execução).

    BASE_URL=http://localhost:8080 python scripts/capturar_prints.py
"""
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080")
SAIDA = Path(__file__).resolve().parent.parent / "docs" / "img"
SAIDA.mkdir(parents=True, exist_ok=True)
for antigo in SAIDA.glob("[0-9][0-9]-*.png"):  # só os prints numerados (preserva o fluxograma)
    antigo.unlink()

with sync_playwright() as p:
    nav = p.chromium.launch()
    pg = nav.new_page(viewport={"width": 1280, "height": 800})

    def abrir(pagina=pg):
        pagina.goto(BASE_URL)
        expect(pagina.locator("#seletor-exemplos option")).not_to_have_count(1)

    def analisar(indice, pagina=pg):
        pagina.select_option("#seletor-exemplos", index=indice)
        pagina.click("#btn-analisar")
        expect(pagina.locator("#painel-lexico")).to_be_visible()

    # 1) Tela inicial
    abrir()
    pg.screenshot(path=SAIDA / "01-tela-inicial.png")

    # 2) Tutorial aberto (com a gramática)
    pg.click("#tutorial > summary")
    pg.click("#tutorial details > summary")
    pg.locator("#tutorial").screenshot(path=SAIDA / "02-tutorial.png")

    # 3) AST do exemplo do enunciado, nó MULTIPLICACAO selecionado
    abrir()
    pg.fill("#entrada-codigo", "int resultado = 10 + 5 * 2;")
    pg.click("#btn-analisar")
    expect(pg.locator("#secao-ast")).to_be_visible()
    pg.locator('#ast-arvore li[data-tipo="MULTIPLICACAO"] > .ast-no__linha .ast-no__rotulo').click()
    pg.locator("#secao-ast").screenshot(path=SAIDA / "03-ast-selecao-de-no.png")

    # 4) Construção passo a passo da árvore
    pg.click("#ast-passo-inicio")
    for _ in range(4):
        pg.click("#ast-passo-proximo")
    pg.locator("#secao-ast").screenshot(path=SAIDA / "04-ast-construcao-passo-a-passo.png")

    # 5) Funções (exemplo 10), visão geral da página
    abrir()
    analisar(10)
    pg.screenshot(path=SAIDA / "05-ast-funcoes-pagina.png", full_page=False)
    pg.locator("#secao-ast").screenshot(path=SAIDA / "06-ast-funcoes.png")

    # 7) Erros sintáticos (exemplo 12)
    abrir()
    pg.select_option("#seletor-exemplos", index=12)
    pg.click("#btn-analisar")
    expect(pg.locator("#erros-sintaticos .erro-item--sint").first).to_be_visible()
    pg.locator("main > .layout").screenshot(path=SAIDA / "07-erros-sintaticos.png")
    pg.locator("#painel-lexico > section").nth(1).screenshot(path=SAIDA / "08-codigo-com-erro-sintatico.png")

    # 9) Erro léxico: o parser não roda
    abrir()
    pg.select_option("#seletor-exemplos", index=8)
    pg.click("#btn-analisar")
    expect(pg.locator("#sintatico-status")).to_contain_text("não executada")
    pg.locator("main > .layout").screenshot(path=SAIDA / "09-erro-lexico-sem-parser.png")

    # 10) Scanner (Etapa 3): passo a passo
    abrir()
    pg.fill("#entrada-codigo", "int numero = 10;\nif (numero <= 5) { numero = 0; }")
    pg.click("#btn-analisar")
    expect(pg.locator("#painel-lexico")).to_be_visible()
    for _ in range(9):
        pg.click("#passo-proximo")
    pg.locator("#painel-lexico > section").first.screenshot(path=SAIDA / "10-scanner-passo-a-passo.png")

    # 11) Entrada vazia e falha de comunicação
    abrir()
    pg.fill("#entrada-codigo", "")
    pg.click("#btn-analisar")
    expect(pg.locator("#resultado")).to_contain_text("Informe um código-fonte")
    pg.screenshot(path=SAIDA / "11-validacao-entrada-vazia.png")
    abrir()
    pg.fill("#entrada-codigo", "int a = 1;\n")
    pg.route("**/api/analisar", lambda r: r.abort())
    pg.click("#btn-analisar")
    expect(pg.locator("#resultado")).to_contain_text("Falha de comunicação")
    pg.screenshot(path=SAIDA / "12-falha-comunicacao.png")

    # 13) Celular: AST
    ctx = nav.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    cel = ctx.new_page()
    abrir(cel)
    cel.fill("#entrada-codigo", "int resultado = 10 + 5 * 2;")
    cel.click("#btn-analisar")
    expect(cel.locator("#secao-ast")).to_be_visible()
    cel.locator('#ast-arvore li[data-tipo="MULTIPLICACAO"] > .ast-no__linha .ast-no__rotulo').click()
    cel.locator("#secao-ast").screenshot(path=SAIDA / "13-celular-ast.png")
    ctx.close()

    nav.close()
print("Prints salvos em", SAIDA)
