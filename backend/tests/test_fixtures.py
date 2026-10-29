"""As fixtures usadas pelos testes do frontend devem refletir a resposta real do backend."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

PASTA = Path(__file__).resolve().parents[2] / "frontend" / "tests" / "fixtures"
ARQUIVOS = sorted(PASTA.glob("*.json")) if PASTA.exists() else []


@pytest.mark.skipif(not ARQUIVOS, reason="fixtures do frontend não encontradas")
@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda p: p.name)
def test_fixture_do_frontend_esta_atualizada(arquivo):
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    real = TestClient(app).post("/api/analisar", json={"codigo": dados["codigo"]}).json()
    assert dados["resposta"] == real, (
        "Fixture desatualizada. Regenere com: cd backend && python ../scripts/gerar_fixtures.py"
    )
