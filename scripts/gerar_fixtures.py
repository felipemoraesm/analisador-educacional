"""Gera as fixtures do frontend a partir da resposta REAL do endpoint /api/analisar.

    cd backend && python ../scripts/gerar_fixtures.py

Os testes de interface usam essas respostas; o teste backend/tests/test_fixtures.py
falha se elas ficarem desatualizadas em relação ao scanner.
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

CASOS = {
    "valido": "int numero = 10;",
    "completo": "int idade = 21;\nfloat altura = 1.75; // comentario\nchar c = 'A';\nif (idade >= 18 && !c) { return 1; }\n",
    "com_erros": "int valor = 10;\nint total = valor @ 2;\nfloat taxa = 3.;\nchar s = \"aberta;\n/* sem fim\n",
    "emoji": "char s = \"😀\"; int x;",
}

if __name__ == "__main__":
    cliente = TestClient(app)
    destino = RAIZ / "frontend" / "tests" / "fixtures"
    destino.mkdir(parents=True, exist_ok=True)
    for nome, codigo in CASOS.items():
        resposta = cliente.post("/api/analisar", json={"codigo": codigo}).json()
        (destino / f"{nome}.json").write_text(
            json.dumps({"codigo": codigo, "resposta": resposta}, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
        )
        print("gerada:", nome)
