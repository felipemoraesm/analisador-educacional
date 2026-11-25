import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StrictStr
from starlette.exceptions import HTTPException as StarletteHTTPException

from .analise import montar_resposta
from .exemplos import EXEMPLOS
from .gramatica import gramatica_completa
from .scanner import tokenizar
from .validacao import validar_codigo

logger = logging.getLogger("analisador")

app = FastAPI(title="Analisador Educacional - Backend", version="0.4.0")

MSG_REQUISICAO_INVALIDA = (
    'Requisição inválida. Envie um JSON no formato {"codigo": "<texto>"}.'
)
MSG_ERRO_INESPERADO = "Ocorreu um erro inesperado. Tente novamente em instantes."


class AnaliseRequest(BaseModel):
    codigo: StrictStr


def _erro(status: int, erro: str, mensagem: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"recebido": False, "erro": erro, "mensagem": mensagem},
    )


@app.exception_handler(RequestValidationError)
async def requisicao_invalida(request: Request, exc: RequestValidationError):
    # Não repassa os detalhes internos do validador ao usuário.
    return _erro(400, "requisicao_invalida", MSG_REQUISICAO_INVALIDA)


@app.exception_handler(StarletteHTTPException)
async def erro_http(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return _erro(404, "nao_encontrado", "Recurso não encontrado.")
    if exc.status_code == 405:
        return _erro(405, "metodo_nao_permitido", "Método não permitido para este recurso.")
    return _erro(exc.status_code, "erro_http", "Não foi possível processar a requisição.")


@app.exception_handler(Exception)
async def erro_inesperado(request: Request, exc: Exception):
    logger.exception("Erro inesperado")  # detalhes só no log do servidor
    return _erro(500, "erro_interno", MSG_ERRO_INESPERADO)


@app.get("/api/hello")
def hello():
    """Mantido da Etapa 1 (teste de regressão)."""
    return {"message": "Hello, World!"}


@app.get("/api/health")
def health():
    """Usado pelo healthcheck do Docker Compose."""
    return {"status": "ok"}


@app.get("/api/exemplos")
def listar_exemplos():
    return {"exemplos": EXEMPLOS}


@app.get("/api/gramatica")
def gramatica():
    """Gramática EBNF do subconjunto, precedência e metadados dos nós da AST."""
    return gramatica_completa()


@app.post("/api/analisar")
def analisar(req: AnaliseRequest):
    """Valida a entrada, executa o scanner (Etapa 3) e, se não houver erros léxicos, o parser (Etapa 4).

    Código com erros léxicos ou sintáticos NÃO é uma requisição inválida: a análise
    foi realizada e os erros fazem parte do resultado (HTTP 200).
    A análise semântica será acrescentada na Etapa 5.
    """
    erro = validar_codigo(req.codigo)
    if erro:
        return _erro(erro.status, erro.codigo, erro.mensagem)

    lexico = tokenizar(req.codigo)
    return montar_resposta(req.codigo, lexico)
