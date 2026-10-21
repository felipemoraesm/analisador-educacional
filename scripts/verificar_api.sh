#!/usr/bin/env bash
# Verificações de ponta a ponta da API e da página, via HTTP, contra a aplicação em execução.
# Uso: ./scripts/verificar_api.sh [URL_BASE]   (padrão: http://localhost:8080)
set -uo pipefail
BASE="${1:-http://localhost:8080}"
falhas=0
total=0

checar() {  # descrição, esperado, obtido
  total=$((total + 1))
  if [[ "$3" == *"$2"* ]]; then echo "  OK   $1"; else echo "  FALHA $1 (esperado: $2 | obtido: $3)"; falhas=$((falhas + 1)); fi
}
post() { curl -s -o /tmp/resp.json -w "%{http_code}" -X POST "$BASE/api/analisar" -H 'Content-Type: application/json' -d "$1"; }

echo "Verificando $BASE"
checar "página inicial contém o título" "Analisador Educacional" "$(curl -s "$BASE/")"
checar "GET /api/hello (Etapa 1)" '"Hello, World!"' "$(curl -s "$BASE/api/hello")"
checar "GET /api/health" '"status":"ok"' "$(curl -s "$BASE/api/health")"
exemplos="$(curl -s "$BASE/api/exemplos" | grep -o '"id"' | wc -l)"
checar "GET /api/exemplos devolve ao menos 3 exemplos" "OK" "$([ "$exemplos" -ge 3 ] && echo OK || echo "$exemplos")"

codigo=$(post '{"codigo":"int numero = 10;"}')
checar "POST código válido -> 200" "200" "$codigo"
checar "POST código válido -> recebido:true" '"recebido":true' "$(cat /tmp/resp.json)"

codigo=$(post '{"codigo":""}')
checar "POST vazio -> 400" "400" "$codigo"
checar "POST vazio -> codigo_vazio" "codigo_vazio" "$(cat /tmp/resp.json)"

codigo=$(post '{"codigo":"   "}')
checar "POST só espaços -> 400" "400" "$codigo"
checar "POST só espaços -> codigo_somente_espacos" "codigo_somente_espacos" "$(cat /tmp/resp.json)"

codigo=$(post '{}')
checar "POST sem o campo 'codigo' -> 400" "400" "$codigo"
checar "POST sem o campo 'codigo' -> requisicao_invalida" "requisicao_invalida" "$(cat /tmp/resp.json)"

codigo=$(post '{"codigo": 123}')
checar "POST com tipo errado -> 400" "400" "$codigo"

codigo=$(post '{codigo: malformado')
checar "POST JSON malformado -> 400" "400" "$codigo"
checar "erro não expõe rastreamento" "OK" "$(grep -qi 'traceback' /tmp/resp.json && echo EXPOSTO || echo OK)"

echo "Resultado: $((total - falhas))/$total verificações aprovadas."
[ "$falhas" -eq 0 ]
