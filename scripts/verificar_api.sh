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
checar "página carrega o módulo de visualização" "visual.js" "$(curl -s "$BASE/")"
checar "página carrega o módulo da árvore (AST)" "arvore.js" "$(curl -s "$BASE/")"
checar "GET /api/gramatica (EBNF)" '"simbolo_inicial":"programa"' "$(curl -s "$BASE/api/gramatica")"
checar "GET /api/hello (Etapa 1)" '"Hello, World!"' "$(curl -s "$BASE/api/hello")"
checar "GET /api/health" '"status":"ok"' "$(curl -s "$BASE/api/health")"
exemplos="$(curl -s "$BASE/api/exemplos" | grep -o '"id"' | wc -l)"
checar "GET /api/exemplos devolve ao menos 3 exemplos" "OK" "$([ "$exemplos" -ge 3 ] && echo OK || echo "$exemplos")"

codigo=$(post '{"codigo":"int numero = 10;"}')
checar "POST código válido -> 200" "200" "$codigo"
checar "POST código válido -> recebido:true" '"recebido":true' "$(cat /tmp/resp.json)"
checar "POST código válido -> sucesso:true" '"sucesso":true' "$(cat /tmp/resp.json)"
checar "scanner: classifica 'int' como palavra reservada" '"tipo":"PALAVRA_RESERVADA","lexema":"int","linha":1,"coluna":1' "$(cat /tmp/resp.json)"
checar "scanner: resumo com 5 tokens" '"total_tokens":5' "$(cat /tmp/resp.json)"

codigo=$(post '{"codigo":"int a = 1 @ 2;"}')
checar "erro léxico continua com HTTP 200" "200" "$codigo"
checar "erro léxico -> sucesso:false" '"sucesso":false' "$(cat /tmp/resp.json)"
checar "erro léxico -> ERRO_LEXICO do '@'" '"tipo":"ERRO_LEXICO","lexema":"@","linha":1,"coluna":11' "$(cat /tmp/resp.json)"

codigo=$(post '{"codigo":"int x = 10\nint y = x + ;"}')
checar "erros sintáticos não geram erro léxico" '"erros":[]' "$(cat /tmp/resp.json)"

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

# ---------- Etapa 4: análise sintática ----------
codigo=$(post '{"codigo":"int resultado = 10 + 5 * 2;"}')
checar "parser: programa válido -> HTTP 200" "200" "$codigo"
checar "parser: sintatico.sucesso true" '"sintatico":{"executado":true,"sucesso":true' "$(cat /tmp/resp.json)"
checar "parser: AST com 7 nós" '"total_nos":7' "$(cat /tmp/resp.json)"
checar "parser: multiplicação é nó da árvore" '"tipo":"MULTIPLICACAO"' "$(cat /tmp/resp.json)"

codigo=$(post '{"codigo":"int numero = 10}"}')
checar "parser: erro sintático -> HTTP 200" "200" "$codigo"
checar "parser: sintatico.sucesso false e ast nula" '"sucesso":false,"mensagem":"Análise sintática concluída com 1 erro sintático; a AST não foi construída.","motivo":null,"ast":null' "$(cat /tmp/resp.json)"
checar "parser: erro na linha 1, coluna 16" '"tipo":"ERRO_SINTATICO","linha":1,"coluna":16' "$(cat /tmp/resp.json)"
checar "parser: esperado ';'" '"esperado":[";"]' "$(cat /tmp/resp.json)"

codigo=$(post '{"codigo":"int a = @;"}')
checar "parser não roda com erro léxico" '"executado":false,"sucesso":null' "$(cat /tmp/resp.json)"

echo "Resultado: $((total - falhas))/$total verificações aprovadas."
[ "$falhas" -eq 0 ]
