"""Gera docs/img/fluxograma.svg e .png (fluxograma da análise para o artigo).

    python scripts/gerar_fluxograma.py
"""
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
W, H = 980, 1010
out = []


def txt(x, y, linhas, size=14, anchor="middle", cor="#1b1f2a", peso="normal"):
    if isinstance(linhas, str):
        linhas = [linhas]
    y0 = y - (len(linhas) - 1) * (size + 3) / 2
    for i, l in enumerate(linhas):
        l = l.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        out.append(f'<text x="{x}" y="{y0 + i * (size + 3) + size * 0.35}" text-anchor="{anchor}" '
                   f'font-size="{size}" fill="{cor}" font-weight="{peso}">{l}</text>')


def caixa(cx, cy, w, h, linhas, fundo="#e8efff", borda="#2f5bea", tracejado=False):
    d = ' stroke-dasharray="6 4"' if tracejado else ""
    out.append(f'<rect x="{cx - w/2}" y="{cy - h/2}" width="{w}" height="{h}" rx="9" fill="{fundo}" stroke="{borda}" stroke-width="2"{d}/>')
    txt(cx, cy, linhas)


def losango(cx, cy, w, h, linhas, fundo="#fff6e0", borda="#d49a00"):
    out.append(f'<polygon points="{cx},{cy-h/2} {cx+w/2},{cy} {cx},{cy+h/2} {cx-w/2},{cy}" fill="{fundo}" stroke="{borda}" stroke-width="2"/>')
    txt(cx, cy, linhas, 13)


def seta(pontos, rotulo=None, lx=0, ly=0, tracejado=False):
    d = " ".join(("M" if i == 0 else "L") + f"{x},{y}" for i, (x, y) in enumerate(pontos))
    t = ' stroke-dasharray="6 4"' if tracejado else ""
    out.append(f'<path d="{d}" fill="none" stroke="#444" stroke-width="2"{t} marker-end="url(#ponta)"/>')
    if rotulo:
        txt(lx, ly, rotulo, 13, "middle", "#444", "bold")


out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Arial, Helvetica, sans-serif" role="img" aria-labelledby="t d">')
out.append('<title id="t">Fluxograma da análise: entrada, análise léxica, análise sintática, análise semântica (a implementar) e apresentação</title>')
out.append('<desc id="d">O código do usuário vai ao backend, é validado e passa pelo scanner. Se houver erro léxico, o parser não roda. Senão, o parser constrói a AST ou reporta erros sintáticos. A análise semântica é a etapa futura. O resultado volta ao frontend.</desc>')
out.append('<defs><marker id="ponta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#444"/></marker></defs>')
out.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

caixa(400, 45, 360, 54, ["Usuário escreve ou escolhe um código em C", "(interface web)"], "#f2f2f2", "#666")
seta([(400, 72), (400, 105)])
caixa(400, 135, 360, 54, ["Frontend: validação local", "(vazio / só espaços) e POST /api/analisar"])
seta([(400, 162), (400, 198)])
caixa(400, 228, 360, 54, ["Backend: validação da entrada", "(vazio, espaços, tamanho, JSON, Unicode)"])
seta([(580, 228), (700, 228)], "inválida", 640, 216)
caixa(820, 228, 220, 54, ["HTTP 400/413", "mensagem de entrada inválida"], "#fdeaea", "#d64545")
seta([(400, 255), (400, 295)], "válida", 430, 277)
caixa(400, 325, 360, 54, ["ANÁLISE LÉXICA (scanner, Etapa 3)", "código → tokens + erros léxicos"], "#e6f6ec", "#2e9d58")
seta([(400, 352), (400, 395)])
losango(400, 440, 250, 90, ["Há erros", "léxicos?"])
seta([(525, 440), (700, 440)], "sim", 612, 428)
caixa(820, 440, 220, 66, ["Parser NÃO executa", "(evita erros em cascata)", "erros léxicos são exibidos"], "#fff6e0", "#d49a00")
seta([(400, 485), (400, 535)], "não", 430, 513)
caixa(400, 565, 360, 54, ["ANÁLISE SINTÁTICA (parser, Etapa 4)", "tokens → AST (descendente recursivo)"], "#efe9fb", "#7a4fd0")
seta([(400, 592), (400, 635)])
losango(400, 680, 250, 90, ["Há erros", "sintáticos?"])
seta([(525, 680), (700, 680)], "sim", 612, 668)
caixa(820, 680, 220, 66, ["AST = nula", "erros com linha, coluna,", "esperado e regra violada"], "#efe9fb", "#7a4fd0")
seta([(400, 725), (400, 770)], "não", 430, 750)
caixa(400, 800, 360, 54, ["AST construída", "(nós com tipo, atributos e posição)"], "#efe9fb", "#7a4fd0")
seta([(400, 827), (400, 865)], tracejado=True)
caixa(400, 892, 360, 54, ["ANÁLISE SEMÂNTICA (Etapa 5, a implementar)", "tabela de símbolos e tipos"], "#f2f2f2", "#888", True)

# quadro final, largo, recebendo cada saída por uma faixa própria
caixa(490, 972, 940, 58, ["Resposta JSON (lexico + sintatico) → Frontend: tabela de tokens, passo a passo do scanner,",
                          "código colorido, erros léxicos/sintáticos e AST navegável com construção animada"])
seta([(930, 440), (948, 440), (948, 943)])                      # erro léxico -> resposta
seta([(930, 680), (966, 680), (966, 943)])                      # erro sintático -> resposta
seta([(580, 800), (700, 800), (700, 943)])                      # AST -> resposta
seta([(580, 892), (640, 892), (640, 943)], tracejado=True)      # semântica (futura) -> resposta
seta([(930, 228), (970, 228), (970, 300), (990, 300)]) if False else None
out.append('</svg>')

svg = RAIZ / "docs" / "img" / "fluxograma.svg"
svg.write_text("\n".join(out), encoding="utf-8")

try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        pg.goto(f"file://{svg}")
        pg.screenshot(path=str(svg.with_suffix(".png")))
        b.close()
except Exception as e:  # o SVG já foi gerado; o PNG é só conveniência
    print("PNG não gerado:", e)
print("Fluxograma gerado em", svg.parent)
