#!/usr/bin/env bash
# Teste de implantação: constrói as imagens, sobe os serviços com Docker Compose,
# espera ficarem saudáveis, executa as verificações HTTP e derruba tudo ao final.
# Uso (na raiz do projeto): ./scripts/testar_implantacao.sh
# Opcional: RODAR_E2E=1 para também executar os testes de navegador (tests/e2e).
set -euo pipefail
cd "$(dirname "$0")/.."
PORTA="${FRONTEND_PORT:-8080}"
BASE="http://localhost:${PORTA}"

limpar() { docker compose down >/dev/null 2>&1 || true; }
trap limpar EXIT

echo "==> Construindo e iniciando os serviços"
docker compose up --build -d

echo "==> Aguardando a aplicação responder em $BASE"
for i in $(seq 1 60); do
  if curl -fsS "$BASE/api/health" >/dev/null 2>&1; then break; fi
  if [ "$i" -eq 60 ]; then
    echo "FALHA: a aplicação não ficou disponível a tempo."; docker compose logs; exit 1
  fi
  sleep 2
done

echo "==> Estado de saúde do backend"
estado="$(docker inspect --format '{{.State.Health.Status}}' analisador-backend)"
echo "  backend: $estado"
[ "$estado" = "healthy" ] || { echo "FALHA: backend não está saudável"; exit 1; }

echo "==> Verificações da API (via Nginx)"
./scripts/verificar_api.sh "$BASE"

if [ "${RODAR_E2E:-0}" = "1" ]; then
  echo "==> Testes de ponta a ponta (navegador)"
  BASE_URL="$BASE" python3 -m pytest tests/e2e -v
fi
echo "==> Implantação verificada com sucesso."
