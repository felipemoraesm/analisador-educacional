"""A gramática documentada, a servida pela API e a usada pelo parser devem ser a mesma."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.gramatica import EBNF, NOS, PRECEDENCIA, regras_dos_tipos
from app.main import app

DOC = Path(__file__).resolve().parents[2] / "docs" / "gramatica.md"
client = TestClient(app)


def test_endpoint_devolve_a_gramatica_completa():
    r = client.get("/api/gramatica")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["simbolo_inicial"] == "programa" and corpo["ebnf"] == EBNF
    assert corpo["precedencia"][0]["operadores"] == ["||"] and corpo["precedencia"][-1]["associatividade"] == "direita"
    assert "PROGRAMA" in corpo["nos"] and "categorias_no" in corpo and "terminais" in corpo


@pytest.mark.skipif(not DOC.exists(), reason="docs/gramatica.md não encontrado")
def test_documento_contem_exatamente_a_ebnf_do_codigo():
    texto = DOC.read_text(encoding="utf-8")
    bloco = re.search(r"```ebnf\n(.*?)\n```", texto, re.S).group(1)
    assert bloco.strip() == EBNF.strip(), "docs/gramatica.md está diferente de app/gramatica.py"


def test_todo_nao_terminal_usado_esta_definido():
    definidos = set(re.findall(r"^(\w+)\s*=", EBNF, re.M))
    usados = set(re.findall(r"\b([a-z_]+)\b", re.sub(r'"[^"]*"', "", EBNF)))
    assert definidos == usados & definidos
    assert len(definidos) == 25
    assert usados - definidos <= set()


def test_regras_dos_nos_citam_nao_terminais_existentes():
    definidos = set(re.findall(r"^(\w+)\s*=", EBNF, re.M))
    for tipo, (regra, descricao, categoria) in NOS.items():
        nome = re.match(r"(\w+)\s*=", regra).group(1)
        assert nome in definidos, tipo
        assert descricao and categoria in ("estrutura", "declaracao", "controle", "expressao", "folha")


def test_precedencia_documentada_corresponde_a_ordem_das_regras():
    ordem = ["ou", "e", "igualdade", "relacional", "soma", "termo", "unario"]
    posicoes = [EBNF.index(f"\n{nome} ") if nome != "ou" else EBNF.index("\nou ") for nome in ordem]
    assert posicoes == sorted(posicoes)
    assert [p["nivel"] for p in PRECEDENCIA] == list(range(1, 8))


def test_regras_dos_tipos_filtra():
    assert set(regras_dos_tipos(["ADICAO", "NAO_EXISTE"])) == {"ADICAO"}


def test_todo_tipo_de_no_produzido_pelo_parser_tem_regra():
    from app.exemplos import EXEMPLOS
    from app.parser import analisar_sintaxe
    from app.scanner import tokenizar
    vistos = set()
    for ex in EXEMPLOS:
        lex = tokenizar(ex["codigo"])
        if lex["sucesso"]:
            r = analisar_sintaxe(lex["tokens"], ex["codigo"])
            if r["sucesso"]:
                vistos |= set(r["resumo"]["por_tipo"])
    assert vistos and vistos <= set(NOS)
