import pytest

from app.validacao import TAMANHO_MAXIMO, validar_codigo


def test_codigo_valido_nao_gera_erro():
    assert validar_codigo("int x = 1;") is None


def test_vazio():
    erro = validar_codigo("")
    assert erro.codigo == "codigo_vazio" and erro.status == 400


@pytest.mark.parametrize("texto", [" ", "   ", "\n", "\t", " \n\t \r\n"])
def test_somente_espacos(texto):
    erro = validar_codigo(texto)
    assert erro.codigo == "codigo_somente_espacos" and erro.status == 400


def test_limite_de_tamanho():
    assert validar_codigo("a" * TAMANHO_MAXIMO) is None
    erro = validar_codigo("a" * (TAMANHO_MAXIMO + 1))
    assert erro.codigo == "codigo_muito_grande" and erro.status == 413


def test_entrada_com_erros_de_programacao_e_aceita():
    # O sistema não presume que o código é válido (erros são tema das etapas futuras)
    assert validar_codigo("int x = 10\nint y = x + ;") is None


def test_surrogate_isolado_e_rejeitado_com_mensagem_clara():
    erro = validar_codigo("int a; \ud800")
    assert erro.codigo == "codigo_invalido" and erro.status == 400
    assert "Unicode" in erro.mensagem


def test_emoji_valido_nao_e_confundido_com_surrogate_isolado():
    assert validar_codigo('char s = "😀";') is None
