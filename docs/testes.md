# Registro de testes

## Ambiente das execuções registradas

- Backend: Uvicorn (Python 3.12, FastAPI) em `127.0.0.1:8000`.
- Frontend: Nginx 1.24 usando **o `frontend/nginx.conf` do projeto** (com o nome `backend` apontando para `127.0.0.1`), na porta 80.
- Navegador: Chromium headless via Playwright (viewport de desktop e de celular emulado).
- **Docker/Docker Compose NÃO foram usados nestas execuções.** O teste de implantação (`scripts/testar_implantacao.sh`) precisa ser executado em uma máquina com Docker (ver "Pendências").

## Etapa 3 – análise léxica

### Execução 1 – conjunto completo

| Funcionalidade / módulo | Tipo | Comando | Aprovados | Reprovados |
|---|---|---|---|---|
| Scanner: palavras reservadas, identificadores, literais (int, real, string, char), operadores (incl. compostos e maior casamento), delimitadores, comentários, espaços, posições (linha/coluna, CRLF, tab, emoji/UTF-16), erros léxicos, casos de borda, `caminho` do autômato, desempenho | Unitário | `cd backend && pytest tests/test_scanner.py` | 154 | 0 |
| Endpoint `/api/analisar` (contrato léxico, erros léxicos com HTTP 200, validações da Etapa 2, 500 sem vazar detalhes), `/api/exemplos`, regressão de `/api/hello` e `/api/health`, validações, fixtures do frontend atualizadas | Unitário + endpoints | `cd backend && pytest tests/test_api.py tests/test_validacao.py tests/test_fixtures.py` | 48 | 0 |
| **Backend (total)** | | `cd backend && pytest` | **202** | 0 |
| Etapa 2 na interface (edição, exemplos, validações, falhas de comunicação, botão, Limpar, Ctrl+Enter) | Interface (jsdom) – regressão | `cd frontend && node --test tests/interface.test.js` | 37 | 0 |
| Etapa 3 na interface (tabela, resumo, cores, sequência, erros, passo a passo, reprodução com relógio falso, segurança contra HTML, limite de linhas) | Interface (jsdom) | `cd frontend && node --test tests/lexico_interface.test.js` | 37 | 0 |
| Cliente do frontend contra backend real (via Nginx): tokens, erros léxicos, exemplos, posições UTF-16, servidor inacessível | Integração | `API_URL=http://localhost npm run test:integracao` | 10 | 0 |
| Fluxo no navegador: tokens na tabela, erros, passo a passo, reprodução, tutorial, layout de celular, regressão da Etapa 2 | Ponta a ponta | `BASE_URL=http://localhost pytest tests/e2e -v` | 25 | 0 |
| Página, API, scanner, validações e vazamento de rastreamento via HTTP | Verificação HTTP | `./scripts/verificar_api.sh http://localhost` | 23 | 0 |

**Total: 334 verificações aprovadas, 0 reprovadas.**

### Regressão (Etapas 1 e 2)

Todos os testes anteriores continuaram sendo executados: `/api/hello` e `/api/health` (backend, integração, E2E e script HTTP), validação de entrada vazia/espaços/JSON inválido (backend, interface, E2E), exemplos, edição, preservação do código e falhas de comunicação (interface e E2E).

### Mudanças intencionais de comportamento (testes atualizados de propósito)

| O que mudou | Por quê | Testes atualizados |
|---|---|---|
| A `mensagem` de `/api/analisar` deixou de ser "Código recebido com sucesso." e passou a descrever a análise léxica ("Análise léxica concluída: N tokens, ...") | O endpoint agora executa o scanner. Os campos `recebido`, `linhas` e `caracteres` foram mantidos | `backend/tests/test_api.py::test_codigo_valido`; `frontend/tests/interface.test.js` (teste "sucesso: mostra mensagem..."); 3 asserções em `tests/e2e/` |
| `test_codigo_com_erros_intencionais_e_recebido` virou `test_codigo_com_erros_sintaticos_e_tokenizado_normalmente` | A especificação diz que tokens válidos com erros sintáticos devem ser tokenizados normalmente | `backend/tests/test_api.py` |

Nenhum teste foi alterado apenas para "passar": nos dois casos o novo requisito está documentado em `docs/scanner.md`.

### Falhas encontradas durante o desenvolvimento e correções

1. **Expectativa errada em teste (não era bug do scanner).** Em `linha 3 */ int b;` esperei coluna 13 para `int`; o correto é 12. Corrigido o teste.
2. **Contagens erradas em dois testes de endpoint** (11 em vez de 10 tokens; 8 em vez de 7). Recontadas à mão e corrigidas nos testes; o código estava certo.
3. **Texto da narração em teste.** O teste esperava "Comentário de bloco..." mas a narração usa "comentário..." em minúscula após "Erro léxico na linha...". Corrigida a expectativa.
4. **Bug real, encontrado em revisão antes de abrir no navegador:** `app.js` usava a variável `raiz` fora do seu escopo ao localizar o módulo `visual.js`. Os testes em Node não detectavam, pois usam `require`; no navegador causaria `ReferenceError`. Corrigido, e os testes E2E passam a cobrir o caminho do navegador.
5. **Defeitos visuais encontrados nos prints:** o lexema em montagem no passo a passo não recebia a cor da categoria, e os cabeçalhos das colunas numéricas da tabela estavam desalinhados. Corrigidos.
6. **Teste fraco substituído.** Um teste de números reais que eu havia escrito não verificava os estados do autômato; foi trocado por um que confere `INT → REAL_PONTO → REAL → REAL`.

## Etapa 2 (histórico)

Na Etapa 2 foram executados 107 testes (36 backend, 37 interface, 6 integração, 13 E2E e 15 verificações HTTP), todos aprovados. Eles foram mantidos e ampliados.

## Pendências e limitações dos testes

- **Executar `./scripts/testar_implantacao.sh` com Docker** (build, healthcheck, Compose) e registrar o resultado abaixo.
- Os testes de interface usam jsdom, que não aplica CSS; a aparência é conferida nos testes de navegador e nos prints.
- Testes de navegador cobrem somente Chromium; o celular é **emulado**, não testado em aparelho real.
- Não há testes de carga nem de acessibilidade automatizada (há `aria-live`, rótulos e `role` nos elementos, mas sem auditoria automática).

## Registro da execução com Docker (preencher)

- Data: ____/____/2026
- Sistema operacional / versões de Docker e Compose: ________
- Comando: `./scripts/testar_implantacao.sh`
- Resultado: ________
