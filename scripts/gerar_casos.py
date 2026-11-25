"""Gera docs/casos-de-teste.md a partir de backend/tests/casos/casos_artigo.json.

Uso (na raiz do repositório):  python scripts/gerar_casos.py
O JSON é a fonte única: os testes automatizados (backend/tests/test_casos_artigo.py)
leem o mesmo arquivo, o que evita divergência entre documentação e testes.
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTE = RAIZ / "backend" / "tests" / "casos" / "casos_artigo.json"
DESTINO = RAIZ / "docs" / "casos-de-teste.md"

CABECALHO = """# Casos de teste (Etapa 4)

> Arquivo gerado por `scripts/gerar_casos.py` a partir de
> `backend/tests/casos/casos_artigo.json`. **Não edite à mão**: altere o JSON e gere de novo.

Os resultados esperados foram escritos a partir da gramática (`docs/gramatica.md`) e do
roteiro da disciplina, e são executados contra a API real por
`backend/tests/test_casos_artigo.py`. Se algum resultado esperado precisar mudar,
registre a mudança e o motivo na seção "Mudanças nos casos" no fim deste arquivo.

{notacao}

Coluna "Verificação": *automatizado* = `backend/tests/test_casos_artigo.py`; *Etapa 5* = depende
da análise semântica (marcado como *skipped*); demais casos indicam o teste ou a verificação manual.
Execução de 13/11/2026: 68 aprovados, 0 reprovados, 7 ignorados (Etapa 5).
Os critérios (C1 a C18) estão em `docs/materiais-e-metodos.md`.

"""

REGISTRO = """
## Registro de execução (preencher na Etapa 6)

| ID | Entrada utilizada | Resultado esperado | Resultado observado | Status (aprovado / reprovado / pendente) | Defeito identificado | Correção realizada |
|---|---|---|---|---|---|---|
| | | | | | | |

## Mudanças nos casos

| Data | Caso | Mudança | Justificativa |
|---|---|---|---|
| | | | |
"""


def _md(texto: str) -> str:
    return texto.replace("|", "\\|").replace("\n", "⏎")


def verificacao(c: dict) -> str:
    if c.get("etapa") == 5:
        return "Etapa 5 (previsto)"
    return c.get("teste", "automatizado")


def main() -> None:
    dados = json.loads(FONTE.read_text(encoding="utf-8"))
    linhas = [CABECALHO.format(notacao="**Notação da AST de referência:** " + dados["notacao_ast"])]
    categoria = None
    for c in dados["casos"]:
        if c["categoria"] != categoria:
            categoria = c["categoria"]
            linhas.append(f"\n## {categoria}\n")
            linhas.append("| ID | Entrada (⏎ = quebra de linha) | Resultado esperado | AST de referência | Análise | Critérios | Verificação |")
            linhas.append("|---|---|---|---|---|---|---|")
        ast = f"`{_md(c['ast'])}`" if "ast" in c else "—"
        linhas.append(
            f"| {c['id']} | `{_md(c['entrada'])}` | {_md(c['esperado'])} | {ast} | "
            f"{c['analise']} | {', '.join(c['criterios'])} | {verificacao(c)} |"
        )
    linhas.append(REGISTRO)
    DESTINO.write_text("\n".join(linhas), encoding="utf-8")
    print(f"{len(dados['casos'])} casos escritos em {DESTINO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
