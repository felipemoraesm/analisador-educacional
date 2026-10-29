"""Gera os prints da interface em docs/img/ (requer a aplicação em execução).

    BASE_URL=http://localhost:8080 python scripts/capturar_prints.py
"""
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080")
SAIDA = Path(__file__).resolve().parent.parent / "docs" / "img"
SAIDA.mkdir(parents=True, exist_ok=True)
for antigo in SAIDA.glob("*.png"):
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

    # 2) Tutorial aberto
    pg.click("#tutorial > summary")
    pg.locator("#tutorial").screenshot(path=SAIDA / "02-tutorial.png")

    # 3) Tokens de um programa válido (exemplo 7: operadores)
    abrir()
    analisar(7)
    pg.screenshot(path=SAIDA / "03-analise-lexica-sucesso.png", full_page=True)

    # 4) Erros léxicos (exemplo 8)
    abrir()
    analisar(8)
    pg.locator("main > .layout").screenshot(path=SAIDA / "04-erros-lexicos.png")

    # 5) Passo a passo (exemplo 1, no meio do lexema 'numero')
    abrir()
    pg.fill("#entrada-codigo", "int numero = 10;\nif (numero <= 5) { numero = 0; }")
    pg.click("#btn-analisar")
    expect(pg.locator("#painel-lexico")).to_be_visible()
    for _ in range(9):
        pg.click("#passo-proximo")
    pg.locator("#painel-lexico > section").first.screenshot(path=SAIDA / "05-passo-a-passo.png")

    # 6) Código colorido + sequência de tokens
    pg.locator("#painel-lexico > section").nth(1).screenshot(path=SAIDA / "06-codigo-colorido.png")

    # 7) Tabela de tokens
    pg.locator("#painel-lexico > section").nth(2).screenshot(path=SAIDA / "07-tabela-de-tokens.png")

    # 8) Entrada vazia
    abrir()
    pg.fill("#entrada-codigo", "")
    pg.click("#btn-analisar")
    expect(pg.locator("#resultado")).to_contain_text("Informe um código-fonte")
    pg.screenshot(path=SAIDA / "08-validacao-entrada-vazia.png")

    # 9) Falha de comunicação
    abrir()
    pg.fill("#entrada-codigo", "int a = 1;\n")
    pg.route("**/api/analisar", lambda r: r.abort())
    pg.click("#btn-analisar")
    expect(pg.locator("#resultado")).to_contain_text("Falha de comunicação")
    pg.screenshot(path=SAIDA / "09-falha-comunicacao.png")

    # 10) Celular
    ctx = nav.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    cel = ctx.new_page()
    abrir(cel)
    cel.screenshot(path=SAIDA / "10-celular-inicio.png")
    analisar(8, cel)
    for _ in range(14):
        cel.click("#passo-proximo")
    cel.locator("#painel-lexico > section").first.screenshot(path=SAIDA / "11-celular-passo-a-passo.png")
    ctx.close()

    nav.close()
print("Prints salvos em", SAIDA)
