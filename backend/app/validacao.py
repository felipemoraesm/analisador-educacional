"""Validações iniciais da entrada. Não faz análise léxica, sintática ou semântica."""

from dataclasses import dataclass
from typing import Optional

TAMANHO_MAXIMO = 20_000  # caracteres

MSG_VAZIO = "Informe um código-fonte antes de solicitar a análise."
MSG_ESPACOS = (
    "O código informado contém apenas espaços em branco. "
    "Digite um programa para analisar."
)
MSG_GRANDE = f"O código excede o limite de {TAMANHO_MAXIMO} caracteres."
MSG_UNICODE = "O código contém caracteres Unicode inválidos (incompletos). Remova-os e tente novamente."


@dataclass(frozen=True)
class ErroEntrada:
    codigo: str  # identificador estável, usado pelo frontend e pelos testes
    mensagem: str
    status: int


def validar_codigo(codigo: str) -> Optional[ErroEntrada]:
    """Retorna None se a entrada pode ser processada; senão, o erro correspondente."""
    if codigo == "":
        return ErroEntrada("codigo_vazio", MSG_VAZIO, 400)
    if codigo.strip() == "":
        return ErroEntrada("codigo_somente_espacos", MSG_ESPACOS, 400)
    if len(codigo) > TAMANHO_MAXIMO:
        return ErroEntrada("codigo_muito_grande", MSG_GRANDE, 413)
    try:
        codigo.encode("utf-8")
    except UnicodeEncodeError:  # surrogate isolado: não dá para serializar a resposta
        return ErroEntrada("codigo_invalido", MSG_UNICODE, 400)
    return None
