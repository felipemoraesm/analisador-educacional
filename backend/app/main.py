from fastapi import FastAPI

app = FastAPI(title="Analisador Educacional - Backend", version="0.1.0")


@app.get("/api/hello")
def hello():
    """Endpoint mínimo que prova que o backend está respondendo."""
    return {"message": "Hello, World!"}


@app.get("/api/health")
def health():
    """Usado pelo healthcheck do Docker Compose."""
    return {"status": "ok"}
