"""Casos de teste documentados no artigo (Tarefa 4, seção Materiais e Métodos).

Fonte única: ``tests/casos/casos_artigo.json`` (também usada por
``scripts/gerar_casos.py`` para gerar ``docs/casos-de-teste.md``). Os resultados
esperados foram escritos a partir da gramática (``docs/gramatica.md``) e do roteiro
da disciplina; este arquivo os executa contra a API real.

Casos de análise semântica (Etapa 5) e casos manuais ficam como ``skip`` com o motivo.
"""

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.exemplos import EXEMPLOS
from app.main import app

DADOS = json.loads((Path(__file__).parent / "casos" / "casos_artigo.json").read_text(encoding="utf-8"))
CASOS = DADOS["casos"]
client = TestClient(app)

BINARIOS = {"ADICAO", "SUBTRACAO", "MULTIPLICACAO", "DIVISAO", "MODULO", "COMPARACAO", "OPERACAO_LOGICA"}


def sexpr(no):
    """Converte um nó da AST (JSON da API) para a notação textual de referência do artigo."""
    t, a = no["tipo"], no.get("atributos", {})
    f = [sexpr(x) for x in no.get("filhos", [])]

    def s(*partes):
        return "(" + " ".join(list(partes) + f) + ")"

    if t in ("PROGRAMA", "BLOCO", "RETORNO"):
        return s(t)
    if t == "DEFINICAO_FUNCAO":
        return s("FUNCAO", a["tipo_retorno"], a["nome"])
    if t == "PARAMETRO":
        return s("PARAM", a["tipo_dado"], a["nome"])
    if t == "DECLARACAO_VARIAVEL":
        return s("DECL", a["tipo_dado"], a["nome"])
    if t == "ATRIBUICAO":
        return s("ATRIB", a["nome"])
    if t == "CONDICIONAL":
        return s("SE")
    if t == "REPETICAO":
        return s("ENQUANTO")
    if t == "CHAMADA_FUNCAO":
        return s("CHAMADA", a["nome"])
    if t in BINARIOS:
        return s(a["operador"])
    if t == "NEGACAO_LOGICA":
        return s("!")
    if t == "MENOS_UNARIO":
        return s("neg")
    if t == "IDENTIFICADOR":
        return a["nome"]
    if t.startswith("LITERAL_"):
        return a["valor"]
    raise AssertionError(f"tipo de nó desconhecido: {t}")


def codigo_de(caso):
    ent = caso["entrada"]
    if ent.startswith("Exemplo ") and ent.endswith(" da interface"):
        return EXEMPLOS[int(ent.split()[1]) - 1]["codigo"]
    gerador = caso.get("gerador")
    if gerador == "parenteses":
        n = caso["n"]
        return "x = " + "(" * n + "1" + ")" * n + ";"
    if gerador == "muitos_erros":
        return "x = ;\n" * 15
    if gerador == "longo":
        linha = "if (a < b && c != 0) { total = total + a * (b - c) / 2; }\n"
        return linha * (19000 // len(linha))
    if gerador == "grande":
        return "a" * 20001
    if gerador == "posicoes":
        return ent
    if "corpo" in caso:
        return caso["corpo"]
    if gerador or ent.startswith("(") or caso.get("teste"):
        return None
    return ent


def analisar(codigo, status=200):
    r = client.post("/api/analisar", json={"codigo": codigo})
    assert r.status_code == status, r.text
    return r.json()


def ids(lista):
    return [c["id"] for c in lista]


def test_ids_unicos_e_campos():
    assert len(ids(CASOS)) == len(set(ids(CASOS)))
    for c in CASOS:
        for campo in ("id", "categoria", "entrada", "esperado", "analise", "criterios"):
            assert campo in c, (c["id"], campo)


COM_AST = [c for c in CASOS if "ast" in c and codigo_de(c) is not None]
SINTATICOS = [c for c in CASOS if c["categoria"] == "Erro sintático"]
LEXICOS = [c for c in CASOS if c["categoria"] == "Erro léxico"] + [c for c in CASOS if c["id"] == "CT-B08"]
SEMANTICOS = [c for c in CASOS if c.get("etapa") == 5]


@pytest.mark.parametrize("caso", COM_AST, ids=ids(COM_AST))
def test_ast_igual_a_referencia(caso):
    sin = analisar(codigo_de(caso))["sintatico"]
    assert sin["executado"] is True and sin["sucesso"] is True, sin["erros"]
    assert sexpr(sin["ast"]) == caso["ast"]


@pytest.mark.parametrize("caso", SINTATICOS, ids=ids(SINTATICOS))
def test_erro_sintatico(caso):
    corpo = analisar(codigo_de(caso))
    assert corpo["erros"] == [], "não deveria haver erro léxico"
    sin = corpo["sintatico"]
    assert sin["executado"] is True and sin["sucesso"] is False and sin["ast"] is None
    esperados, obtidos = caso["erros"], sin["erros"]
    assert len(obtidos) == len(esperados), [(o["linha"], o["coluna"], o["mensagem"]) for o in obtidos]
    for esp, obt in zip(esperados, obtidos):
        assert obt["tipo"] == "ERRO_SINTATICO"
        assert obt["linha"] == esp["linha"]
        if "coluna" in esp:
            assert obt["coluna"] == esp["coluna"], obt["mensagem"]
        if "esperado" in esp:
            assert set(esp["esperado"]) <= set(obt["esperado"]), obt["esperado"]
        assert obt["mensagem"] and obt["encontrado"]
        # "regra" é null quando o erro ocorre no início de uma instrução (observado na execução
        # de 13/11/2026 e registrado no artigo); nos demais casos traz a regra EBNF.
        assert "regra" in obt


@pytest.mark.parametrize("caso", LEXICOS, ids=ids(LEXICOS))
def test_erro_lexico_impede_o_parser(caso):
    corpo = analisar(codigo_de(caso))
    assert corpo["erros"], "deveria haver erro léxico"
    if caso.get("erros"):
        assert [(e["linha"], e["coluna"]) for e in corpo["erros"]] == [(e["linha"], e["coluna"]) for e in caso["erros"]]
    sin = corpo["sintatico"]
    assert sin["executado"] is False and sin["sucesso"] is None and sin["ast"] is None and sin["motivo"]


@pytest.mark.parametrize("caso", SEMANTICOS, ids=ids(SEMANTICOS))
def test_semantico_previsto(caso):
    pytest.skip("análise semântica prevista para a Etapa 5")


def _caso(id_):
    return next(c for c in CASOS if c["id"] == id_)


@pytest.mark.parametrize("id_", ["CT-B01", "CT-B02", "CT-B07"])
def test_validacao_de_entrada(id_):
    c = _caso(id_)
    analisar(codigo_de(c), status=c["http"])


def test_b06_aninhamento_acima_do_limite():
    sin = analisar(codigo_de(_caso("CT-B06")))["sintatico"]
    assert sin["sucesso"] is False and "aninhamento" in sin["erros"][0]["mensagem"]


def test_b09_limite_de_erros():
    sin = analisar(codigo_de(_caso("CT-B09")))["sintatico"]
    assert len(sin["erros"]) == 10 and sin["erros_truncados"] is True


def test_b10_desempenho():
    codigo = codigo_de(_caso("CT-B10"))
    assert 18000 <= len(codigo) <= 20000
    t0 = time.perf_counter()
    sin = analisar(codigo)["sintatico"]
    assert sin["sucesso"] is True
    assert time.perf_counter() - t0 < 2.0


def test_b11_json_invalido():
    r = client.post("/api/analisar", content=b"{nao e json", headers={"Content-Type": "application/json"})
    assert r.status_code == 400
    r = client.post("/api/analisar", json={"outro": "x"})
    assert r.status_code == 400


def _nos(no):
    yield no
    for f in no["filhos"]:
        yield from _nos(f)


def _consistente(corpo):
    tokens = corpo["tokens"]
    for no in _nos(corpo["sintatico"]["ast"]):
        for f in no["filhos"]:
            assert no["inicio"] <= f["inicio"] and f["fim"] <= no["fim"], (no["tipo"], f["tipo"])
        if no["tipo"] == "IDENTIFICADOR" or no["tipo"].startswith("LITERAL_"):
            # o trecho de um nó inclui parênteses de agrupamento (docs/parser.md), por isso
            # procura-se o token com o mesmo lexema dentro do trecho do nó
            lexema = no["atributos"].get("nome", no["atributos"].get("valor"))
            par = [t for t in tokens if no["inicio"] <= t["inicio"] and t["fim"] <= no["fim"]
                   and t["lexema"] == lexema]
            assert len(par) == 1, f"folha sem token correspondente: {no['tipo']} {no['inicio']}"


def test_b12_posicoes_com_crlf_e_tab():
    _consistente(analisar(_caso("CT-B12")["entrada"]))


def test_f01_exemplos():
    for n, ex in enumerate(EXEMPLOS, start=1):
        corpo = analisar(ex["codigo"])
        if n == 8:
            assert corpo["erros"] and corpo["sintatico"]["executado"] is False
        elif n in (5, 12):
            assert corpo["sintatico"]["sucesso"] is False, n
        else:
            assert corpo["sintatico"]["sucesso"] is True, (n, corpo["sintatico"]["erros"])


def test_f02_consistencia_em_todos_os_validos():
    for c in COM_AST:
        _consistente(analisar(codigo_de(c)))


def test_f04_contrato_da_etapa3_preservado():
    corpo = analisar("int x = 1;")
    for campo, tipo in [("recebido", bool), ("sucesso", bool), ("mensagem", str), ("linhas", int),
                        ("caracteres", int), ("tokens", list), ("erros", list), ("comentarios", list), ("resumo", dict)]:
        assert isinstance(corpo[campo], tipo), campo
    assert corpo["mensagem"].startswith("Análise léxica")
