# Registro de testes

## Ambiente das execuções registradas

- Backend: Uvicorn (Python 3.12, FastAPI) em `127.0.0.1:8000`.
- Frontend: Nginx 1.24 usando **o `frontend/nginx.conf` do projeto** (com o nome `backend` apontando para `127.0.0.1`), na porta 80.
- Navegador: Chromium headless via Playwright (desktop e celular **emulado**).
- As suítes da tabela abaixo foram executadas **fora de contêineres**. A implantação com Docker Compose foi verificada separadamente em 24/11/2026 (ver "Registro da execução com Docker").

## Etapa 4 – análise sintática e AST

### Execução 1 – conjunto completo

| Funcionalidade / módulo | Tipo | Comando | Aprovados | Reprovados |
|---|---|---|---|---|
| Scanner (inclui `void` e posições finais dos tokens) | Unitário | `cd backend && pytest tests/test_scanner.py` | 159 | 0 |
| **Parser**: construções válidas, precedência e associatividade, estrutura e posições da AST, cada tipo de erro, recuperação, limites, fuzz (800 sequências aleatórias), programas aleatórios gerados pela gramática, avaliação independente de 400 expressões | Unitário | `cd backend && pytest tests/test_parser.py` | 114 | 0 |
| Gramática: EBNF do código = `docs/gramatica.md` = `GET /api/gramatica` | Unitário + endpoint | `cd backend && pytest tests/test_gramatica.py` | 7 | 0 |
| Endpoint `/api/analisar` (contrato léxico e sintático, regressão de Etapas 1 a 3, erros sem vazar detalhes) | Endpoints | `cd backend && pytest tests/test_api.py` | 49 | 0 |
| Validações de entrada (inclui Unicode inválido) | Unitário | `cd backend && pytest tests/test_validacao.py` | 11 | 0 |
| Fixtures do frontend iguais à resposta real do backend | Contrato | `cd backend && pytest tests/test_fixtures.py` | 7 | 0 |
| **Backend (total)** | | `cd backend && pytest` | **347** | 0 |
| Etapa 2 na interface (regressão) | Interface (jsdom) | `cd frontend && node --test tests/interface.test.js` | 37 | 0 |
| Etapa 3 na interface (tokens, erros léxicos, passo a passo do scanner) | Interface (jsdom) | `node --test tests/lexico_interface.test.js` | 37 | 0 |
| Etapa 4 na interface (status, erros sintáticos, árvore, seleção/destaque, filtro, exportação, construção animada, consistência tokens × AST, árvore grande, segurança contra HTML) | Interface (jsdom) | `node --test tests/sintatico_interface.test.js` | 42 | 0 |
| Cliente do frontend contra o backend real (via Nginx): tokens, AST, erros, decisão sobre erro léxico, exemplos, gramática, posições UTF-16 | Integração | `API_URL=http://localhost npm run test:integracao` | 16 | 0 |
| Fluxo no navegador: AST e precedência, destaque nó ↔ código, funções, erros sintáticos sem cascata, erro léxico sem parser, construção animada, exportação de JSON, gramática no tutorial, entrada no limite, celular | Ponta a ponta | `BASE_URL=http://localhost pytest tests/e2e -v` | 41 | 0 |
| Página, API, scanner, parser, validações e vazamento de rastreamento via HTTP | Verificação HTTP | `./scripts/verificar_api.sh http://localhost` | 34 | 0 |

**Total: 554 verificações aprovadas, 0 reprovadas.**

### Regressão (Etapas 1 a 3)

Todos os testes anteriores continuam no conjunto e passam: `/api/hello` e `/api/health`; validação de vazio, espaços e JSON inválido; exemplos, edição e falhas de comunicação; scanner (tokens, posições, erros léxicos); tabela de tokens, código colorido e passo a passo do scanner; os campos da Etapa 3 no nível superior da resposta.

### Mudanças intencionais (testes atualizados de propósito)

| O que mudou | Por quê | Testes atualizados |
|---|---|---|
| Palavra reservada `void` no scanner | funções sem retorno (gramática da Etapa 4) | `test_conjunto_de_palavras_reservadas_documentado` |
| Tokens ganharam `fim_linha` e `fim_coluna` | o parser registra o trecho final de cada nó da AST | `test_resposta_lexica_segue_o_contrato` (token exato) |
| A resposta ganhou `lexico` e `sintatico` (os campos da Etapa 3 foram **mantidos**) | contrato da Etapa 4 | `test_resposta_lexica_segue_o_contrato` (conjunto de chaves) |
| O aviso sob o resultado passou a falar só da análise semântica | a sintática agora existe | `frontend/tests/interface.test.js` ("sucesso: mostra mensagem...") e 1 asserção em `tests/e2e/` |
| Uma entrada com Unicode inválido agora devolve HTTP 400 em vez de 500 | correção de defeito | testes novos |

Nenhum teste foi alterado apenas para "passar": em todos os casos o novo requisito está documentado (`docs/gramatica.md`, `docs/parser.md`).

### Falhas encontradas durante o desenvolvimento e correções

**Defeitos reais no código (corrigidos):**

1. **Erro 500 com Unicode inválido** (um *surrogate* isolado, como `\ud800`): a serialização da resposta falhava. Defeito latente da Etapa 3, descoberto ao revisar a robustez do parser. Agora a validação devolve HTTP 400 com mensagem clara.
2. **Contador de profundidade do parser "vazava"**: `entrar()` incrementava antes de lançar o erro de limite. Achado em revisão de código; corrigido para verificar antes de incrementar.
3. **`else` órfão em cascata** depois de um `if` com erro: a proteção era desativada pelas instruções do bloco seguinte. Corrigida para lembrar o nível de bloco em que o `if` falhou.
4. **Palavra reservada ofensora reiniciava a análise** (`int while = 5;` gerava 2 erros; função dentro de função gerava 2). Corrigido: ela é pulada na sincronização (exceto no caso do `;` esquecido).
5. **Concordância nas mensagens** ("foi encontrado a palavra reservada" → "foi encontrada"), vista na saída real ao gerar `docs/parser.md`.
6. **Script de prints apagava o `fluxograma.png`**: passou a apagar só os prints numerados.

**Expectativas erradas nos próprios testes (o código estava certo):**

7. `int numero = 10 }` tem o `}` na coluna 17 (a coluna 16 do enunciado vale para `10}`); em `if (x > 0 {` o `{` está na coluna 11, não 12; `(1 +` sozinho não é instrução válida; contagens erradas de tokens e de folhas; `aria-level` de `MULTIPLICACAO` é 4, não 5; maiúscula em uma asserção de mensagem (a interface começa em minúscula após o prefixo).

**Observação:** os testes foram escritos com apoio de IA e revisados contra a **gramática**, não contra o comportamento do código. Dois testes são verificações independentes: a avaliação de 400 expressões aleatórias contra o Python e a geração aleatória de 200 programas a partir da gramática.

## Etapa 4 – casos de teste do artigo (13/11/2026)

- `backend/tests/test_casos_artigo.py` executa os 78 casos documentados em `docs/casos-de-teste.md` (fonte: `backend/tests/casos/casos_artigo.json`), escritos a partir da gramática e do roteiro.
- Resultado: `cd backend && pytest tests/test_casos_artigo.py` → **68 aprovados, 0 reprovados, 7 ignorados** (casos semânticos da Etapa 5). Backend completo: **415 aprovados, 7 ignorados** (os 347 anteriores continuam aprovados). Interface (jsdom) reexecutada: 116 aprovados. Integração, ponta a ponta e verificação HTTP **não** foram reexecutadas nesta atualização (nenhum código de produção mudou).
- **Expectativas erradas nos casos novos (o código estava certo):** (1) a verificação de consistência exigia que a folha da AST tivesse exatamente o trecho do token, mas, como documentado em `docs/parser.md`, o trecho de um nó inclui os parênteses de agrupamento (`x = ((1));`); a verificação passou a procurar o token dentro do trecho do nó; (2) exigia `regra` preenchida em todo erro.
- **Observação registrada:** erros no início de uma instrução (`10 = x;`, `;` sozinho) trazem `regra = null`. Não é defeito de funcionamento (a mensagem e o `esperado` estão corretos), mas contraria a descrição "todo erro informa a regra violada"; fica como melhoria possível.
- Nenhum teste anterior foi alterado e nenhum código de produção foi modificado.

## Etapa 3 (histórico)

334 verificações aprovadas na ocasião (154 do scanner, 48 de endpoints, 37 + 37 de interface, 10 de integração, 25 de navegador, 23 HTTP). Todas foram mantidas e ampliadas.

## Etapa 2 (histórico)

107 verificações aprovadas (36 backend, 37 interface, 6 integração, 13 navegador, 15 HTTP).

## Pendências e limitações dos testes

- O diferencial opcional com Ollama **não** foi implementado.
- Os testes de interface usam jsdom, que não aplica CSS; a aparência é conferida nos testes de navegador e nos prints.
- Testes de navegador cobrem somente Chromium; o celular é **emulado**, não testado em aparelho real.
- **Não houve avaliação com estudantes**: os testes verificam correção técnica, não eficácia pedagógica.
- Não há auditoria automática de acessibilidade (há `role`, `aria-*` e versão em texto da árvore).

## Registro da execução com Docker

- Data: 24/11/2026
- Sistema operacional / versões de Docker e Compose: Windows 11 / Docker 29.8.2 / Docker Compose v5.6.0
- Comando: `bash scripts/testar_implantacao.sh` (Git Bash)
- Resultado: **Aprovado**
  - Imagens `projeto-compiladores-backend` e `projeto-compiladores-frontend` construídas (≈18 s).
  - Contêiner `analisador-backend` com healthcheck `healthy`; `analisador-frontend` iniciado.
  - `scripts/verificar_api.sh` via Nginx nos contêineres: **34/34 verificações aprovadas** (página e módulos, `/api/gramatica`, `/api/hello`, `/api/health`, `/api/exemplos`, scanner, erros léxicos, validações de entrada, ausência de rastreamento, parser com AST, erro sintático com linha/coluna e esperado, parser não executado com erro léxico).
  - Testes de ponta a ponta (`RODAR_E2E=1`) não foram executados dentro desta verificação; a execução registrada acima, fora de contêineres, teve 41/41 aprovados.
