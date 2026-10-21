# Registro de testes – Etapa 2

## Ambiente das execuções registradas

- Backend: Uvicorn (Python 3.12, FastAPI) em `127.0.0.1:8000`.
- Frontend: Nginx 1.24 usando **o `frontend/nginx.conf` do projeto** (com o nome `backend` apontando para `127.0.0.1`), na porta 80.
- Navegador: Chromium headless via Playwright.
- **Docker/Docker Compose NÃO foram usados nessas execuções.** Os testes de implantação (`scripts/testar_implantacao.sh`) ainda precisam ser executados em uma máquina com Docker (ver "Pendências").

## Execução 1 – conjunto completo (versão final da etapa)

| Funcionalidade / módulo | Tipo | Comando | Aprovados | Reprovados |
|---|---|---|---|---|
| Validações de entrada, endpoints `/api/analisar`, `/api/exemplos`, regressão de `/api/hello` e `/api/health`, erros 400/404/405/413/500 | Unitário + endpoints | `cd backend && pytest` | 36 | 0 |
| Estrutura da tela, edição, preservação e envio do código, exemplos, mensagens de erro, estado do botão, Limpar, Ctrl+Enter | Interface (jsdom) | `cd frontend && node --test tests/interface.test.js` | 37 | 0 |
| Cliente do frontend contra backend real (via Nginx), exemplos reais, caracteres especiais, servidor inacessível | Integração | `API_URL=http://localhost npm run test:integracao` | 6 | 0 |
| Fluxo completo no navegador: exemplo → edição → análise, vazio, espaços, falha de rede, erro 500, recuperação, backend sem frontend, regressão da Etapa 1 | Ponta a ponta | `BASE_URL=http://localhost pytest tests/e2e -v` | 13 | 0 |
| Página, API, validações e vazamento de rastreamento via HTTP | Verificação HTTP | `./scripts/verificar_api.sh http://localhost` | 15 | 0 |

Total: 107 verificações aprovadas, 0 reprovadas.

## Falhas encontradas durante o desenvolvimento e correções

1. **Teste incorreto (não era falha do código).** `contar('a\r\nb\r\n')` esperava 5 caracteres, mas a string tem 6. A expectativa do teste estava errada; o código estava correto. Corrigida a expectativa.
2. **Comando de teste.** `node --test tests/` falhou ao tentar tratar a pasta como módulo. O script `npm test` passou a listar os arquivos de teste explicitamente.
3. **Nginx devolvendo 502.** Em uma execução, o backend havia sido encerrado e o Nginx respondeu 502 (HTML). Isso confirmou na prática o tratamento de 502/503/504 como "falha de comunicação" no frontend (também coberto por teste automatizado).

## Cobertura dos casos exigidos

- Código válido, vazio, só espaços e caracteres especiais: `backend/tests/`, `frontend/tests/interface.test.js`, `tests/e2e/`.
- Edição, preservação e envio do código: interface e ponta a ponta.
- Seleção de cada exemplo, substituição do conteúdo anterior, edição posterior: interface e ponta a ponta.
- Códigos HTTP, formato das respostas, campos ausentes/inválidos, JSON malformado: `backend/tests/test_api.py`, `scripts/verificar_api.sh`.
- Falha de comunicação e erro inesperado: interface e ponta a ponta.
- Regressão da Etapa 1: `/api/hello` e `/api/health` em `test_api.py`, `integracao.test.js`, `tests/e2e/` e `verificar_api.sh`.

## Pendências e limitações dos testes

- **Executar `./scripts/testar_implantacao.sh` com Docker** (build das imagens, healthcheck, Compose) e registrar o resultado abaixo.
- Os testes de interface usam jsdom, que não aplica CSS; a aparência é conferida apenas nos testes de navegador (fonte monoespaçada e altura da área) e nos prints.
- Testes de navegador cobrem somente Chromium.
- Não há testes de carga nem de acessibilidade automatizada.

## Registro da execução com Docker (preencher)

- Data: ____/____/2026
- Sistema operacional / versões de Docker e Compose: ________
- Comando: `./scripts/testar_implantacao.sh`
- Resultado: ________
