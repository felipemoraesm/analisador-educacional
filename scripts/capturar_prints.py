"""Gera os prints da interface em docs/img/ (requer a aplicação em execução).

    BASE_URL=http://localhost:8080 python scripts/capturar_prints.py
"""
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080")
SAIDA = Path(__file__).resolve().parent.parent / "docs" / "img"
SAIDA.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    nav = p.chromium.launch()
    pg = nav.new_page(viewport={"width": 1280, "height": 760})

    def abrir():
        pg.goto(BASE_URL)
        expect(pg.locator("#seletor-exemplos option")).not_to_have_count(1)

    # 1) Estado inicial
    abrir()
    pg.screenshot(path=SAIDA / "01-tela-inicial.png")

    # 2) Exemplo carregado e analisado com sucesso
    abrir()
    pg.select_option("#seletor-exemplos", index=4)  # if/else com comentário
    pg.click("#btn-analisar")
    expect(pg.locator("#resultado")).to_contain_text("Código recebido com sucesso.")
    pg.screenshot(path=SAIDA / "02-exemplo-analisado.png")

    # 3) Entrada vazia
    abrir()
    pg.fill("#entrada-codigo", "")
    pg.click("#btn-analisar")
    expect(pg.locator("#resultado")).to_contain_text("Informe um código-fonte")
    pg.screenshot(path=SAIDA / "03-validacao-entrada-vazia.png")

    # 4) Falha de comunicação (requisição bloqueada no navegador)
    abrir()
    pg.fill("#entrada-codigo", "int a = 1;\n")
    pg.route("**/api/analisar", lambda r: r.abort())
    pg.click("#btn-analisar")
    expect(pg.locator("#resultado")).to_contain_text("Falha de comunicação")
    pg.screenshot(path=SAIDA / "04-falha-comunicacao.png")

    nav.close()
print("Prints salvos em", SAIDA)
