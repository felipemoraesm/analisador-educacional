"""Monta a resposta completa de /api/analisar a partir dos resultados do scanner e do parser.

Decisão de projeto sobre erros léxicos (Etapa 4): quando o scanner encontra
algum erro léxico, o parser NÃO é executado. Uma sequência de tokens com
lacunas produziria diagnósticos sintáticos sem sentido (erros em cascata). Os
erros léxicos continuam sendo apresentados normalmente, e a resposta informa em
``sintatico.motivo`` por que a análise sintática não rodou.
"""

from .parser import analisar_sintaxe, nao_executado

MOTIVO_ERROS_LEXICOS = (
    "A análise sintática não foi executada porque o código tem erros léxicos. "
    "Corrija-os primeiro: com tokens inválidos, os erros sintáticos seriam enganosos."
)


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def mensagem_lexica(resumo: dict) -> str:
    tokens = _plural(resumo["total_tokens"], "token", "tokens")
    if resumo["total_erros"] == 0:
        return f"Análise léxica concluída: {tokens}, nenhum erro léxico."
    erros = _plural(resumo["total_erros"], "erro léxico", "erros léxicos")
    return f"Análise léxica concluída: {tokens} e {erros}."


def montar_resposta(codigo: str, lexico: dict) -> dict:
    """Resposta da API. Mantém todos os campos da Etapa 3 no nível superior e acrescenta
    ``lexico`` (resultado léxico agrupado) e ``sintatico`` (Etapa 4)."""
    if lexico["sucesso"]:
        sintatico = analisar_sintaxe(lexico["tokens"], codigo)
    else:
        sintatico = nao_executado(MOTIVO_ERROS_LEXICOS)

    return {
        # ---- campos da Etapa 3 (preservados) ----
        "recebido": True,
        "sucesso": lexico["sucesso"],
        "mensagem": mensagem_lexica(lexico["resumo"]),
        "linhas": len(codigo.splitlines()),
        "caracteres": len(codigo),
        "tokens": lexico["tokens"],
        "erros": lexico["erros"],
        "comentarios": lexico["comentarios"],
        "resumo": lexico["resumo"],
        # ---- Etapa 4 ----
        "lexico": {
            "sucesso": lexico["sucesso"],
            "tokens": lexico["tokens"],
            "erros": lexico["erros"],
            "comentarios": lexico["comentarios"],
            "resumo": lexico["resumo"],
        },
        "sintatico": sintatico,
    }
