# Registros para o artigo: Materiais e Métodos (Etapa 4)

Este documento reúne, para a seção de **Materiais e Métodos** do artigo, as decisões técnicas, os critérios de avaliação definidos **antes** de interpretar resultados e os casos de teste. Ele descreve apenas o que foi implementado e verificado.

## 1. Fluxo do sistema

Ver [`fluxograma.md`](fluxograma.md): entrada → análise léxica → análise sintática → análise semântica (ainda por implementar) → apresentação dos resultados.

## 2. Materiais (tecnologias)

| Componente | Tecnologia | Observação |
|---|---|---|
| Linguagem analisada | subconjunto de C | escopo léxico em `escopo-lexico.md`, gramática em `gramatica.md` |
| Scanner | Python, autômato escrito à mão | sem geradores (Flex/Ply) |
| Parser | Python, descendente recursivo escrito à mão | gramática EBNF própria; AST própria |
| API | FastAPI | `POST /api/analisar`, `GET /api/gramatica`, `GET /api/exemplos` |
| Interface | HTML, CSS e JavaScript puros | sem bibliotecas de visualização; árvore em DOM com roles ARIA |
| Implantação | Docker Compose (Nginx + backend) | sem novas dependências na Etapa 4 |

## 3. Métodos: decisões técnicas do parser

| Decisão | Escolha | Justificativa |
|---|---|---|
| Estratégia | Descendente recursivo | mapeamento direto regra → método; didático; mensagens contextuais |
| Ferramenta | nenhuma (à mão) | evita ocultar a estrutura que se quer ensinar; sem etapa de geração no build |
| Precedência e associatividade | um método por nível; laços `{ }` para associar à esquerda | a própria estrutura da gramática as define |
| Erros léxicos | o parser **não** roda | tokens com lacunas gerariam diagnósticos enganosos |
| Erros sintáticos | modo pânico, até 10 erros, anti-cascata | o estudante vê vários problemas de uma vez, sem ruído |
| Representação | AST (e não árvore de derivação); texto indentado e JSON | simplificada; posições em cada nó para a Etapa 5 |
| Visualização | árvore navegável + construção passo a passo | relaciona nó ↔ trecho do código ↔ regra ↔ tokens |
| Limites | 40 níveis de aninhamento, altura 120, 20.000 caracteres | evita estourar a pilha e travar a interface |

Detalhes e justificativas completas: [`parser.md`](parser.md).

## 4. Critérios de avaliação (definidos antes da execução)

| # | Critério | Como foi verificado |
|---|---|---|
| C1 | **Aceitação correta**: programas válidos do subconjunto são aceitos (não só os exemplos prontos) | testes por construção; geração aleatória de programas a partir da gramática (200 casos) |
| C2 | **Rejeição correta**: construções inválidas geram erro (e nunca uma AST) | testes de cada tipo de erro; AST nula quando há erro |
| C3 | **Precedência e associatividade** | testes dos exemplos do enunciado e de cada nível; **verificação independente**: o valor da AST de 400 expressões aleatórias é comparado com a avaliação do mesmo texto pelo Python |
| C4 | **Qualidade dos diagnósticos**: posição correta; `esperado`/`encontrado` coerentes; regra violada; sem cascata | testes que conferem linha, coluna, campos e mensagem; casos típicos com 1 erro esperado |
| C5 | **Robustez** | 800 sequências aleatórias de tokens: o parser sempre termina de forma consistente; entradas gigantes e aninhamento extremo não geram falha |
| C6 | **Consistência entre visualizações**: tokens da tabela × folhas da AST × posições | testes de interface e do parser que cruzam folhas da AST com tokens (tipo, lexema, linha, coluna) |
| C7 | **Regressão** das Etapas 1 a 3 | todos os testes anteriores continuam no conjunto |
| C8 | **Desempenho** com entrada no limite | 20.000 caracteres em poucos segundos; interface continua respondendo |
| C9 | **Reprodutibilidade** em ambiente limpo | `scripts/testar_implantacao.sh` após remoção completa, em dois sistemas operacionais: **pendente** |
| C10 | **Documentação** | checklist do README (objetivo, escopo, gramática, execução, exemplos, contrato, testes, limitações) |
| C11 | Correção semântica (Etapa 5) | casos CT-SE de `casos-de-teste.md`: **previsto** |
| C12 | Clareza das mensagens (inspeção) | checklist por mensagem: fase, posição, esperado, encontrado, regra, dica, sem jargão não explicado, coerente com o trecho destacado; 2 avaliadores |
| C13 | Eficácia das mensagens (participantes) | 1ª edição após cada erro deliberado, rubrica FIX/PART/DIFF/UNR/DEL (Marceau et al., 2011), 2 codificadores; meta ≥ 70% FIX+PART, kappa ≥ 0,8 |
| C14 | Clareza das visualizações | tarefas T3 e T5 e itens Q4, Q5, D3 do formulário; meta acerto ≥ 70%, média ≥ 4 |
| C15 | Usabilidade | SUS, sucesso e tempo nas tarefas; meta SUS ≥ 70, sucesso ≥ 80% |
| C16 | Percepção do diferencial | itens D1–D9; meta média ≥ 4 e ≥ 70% de concordância |
| C17 | Acessibilidade básica | uso só com teclado, categorias por cor + símbolo + texto, contraste verificado |
| C18 | Responsividade | 360 px sem rolagem horizontal (emulação) e pelo menos um celular real |

**Mudança registrada (13/11/2026):** o antigo C9 ("usabilidade e aprendizagem com estudantes — não avaliado") foi desdobrado em C12–C16, com instrumento e metas definidos antes da coleta (formulário em [`avaliacao/formulario.md`](avaliacao/formulario.md)); C9–C11 e C17–C18 foram acrescentados para cobrir reprodutibilidade, documentação, a Etapa 5, acessibilidade e celular. C1–C8 não mudaram. Ganho de aprendizagem continua **fora** do escopo desta avaliação.

## 5. Casos de teste

Os 78 casos do artigo (válidos, erros léxicos, erros sintáticos, erros semânticos previstos, borda e fluxo) estão em [`casos-de-teste.md`](casos-de-teste.md), gerado de `backend/tests/casos/casos_artigo.json` e executado por `backend/tests/test_casos_artigo.py` (13/11/2026: 68 aprovados, 0 reprovados, 7 ignorados por dependerem da Etapa 5). Os casos abaixo, do registro original, continuam cobertos por `test_parser.py`.

### Válidos (devem gerar AST)

| Caso | Verificação |
|---|---|
| `int resultado = 10 + 5 * 2;` | `*` abaixo de `+` |
| `int r = 20 - 5 - 3;` | `(20 - 5) - 3` |
| `int r = (10 + 5) * 2;` | parênteses mudam a árvore |
| `if / else if / else`, `while`, blocos aninhados, `return` com e sem valor | estrutura e papéis dos filhos |
| funções com parâmetros e chamadas aninhadas | `DEFINICAO_FUNCAO`, `PARAMETRO`, `CHAMADA_FUNCAO` |
| programa vazio e só comentários | `PROGRAMA` sem filhos |

### Inválidos (devem gerar erros sintáticos)

| Caso | Erro esperado |
|---|---|
| `int numero = 10}` | linha 1, coluna 16: esperado `;`, encontrado `}` |
| `if (x > 0 { ... }` | esperado `)` para fechar a condição do if; sem erro em cascata no `else` |
| `int y = x + ;` e `int x = 1 + * 2;` | expressão sem operando; operadores consecutivos |
| `else { ... }` sem `if` | `else` sem `if` correspondente |
| `int while = 5;` | palavra reservada no lugar de nome (1 erro, sem cascata) |
| `{ int x = 1;` | fim inesperado: bloco aberto na linha 1 não foi fechado |
| `int f(int a);`, `void v;`, `int f(int a, b) {}` | protótipo, `void` fora de lugar, parâmetro sem tipo |

### Entradas com erro léxico

`int a = @;` → o parser não é executado e o motivo é informado; o erro léxico continua sendo exibido.

## 6. Resultados dos testes automatizados

554 verificações aprovadas, 0 reprovadas (detalhe e comandos em [`testes.md`](testes.md)). Falhas encontradas no desenvolvimento e corrigidas: erros em cascata (`else` órfão; palavra reservada que reinicia a análise), um vazamento do contador de profundidade, um erro 500 com Unicode inválido e concordância de gênero em mensagens.

## 7. Comparação com a literatura estudada

A comparação completa, com dez fontes (Tarefas 1 a 4), a matriz de características com ✓/✗/NI/N/A e a análise de usabilidade, acessibilidade e celulares, está no artigo (Tarefa 4, seções 4 a 6). Resumo do que importa para este repositório:

- Nenhuma das fontes analisa um subconjunto declarado da própria linguagem C (usam pseudolinguagem, DSLs, gramáticas arbitrárias, linguagens próprias inspiradas em C ou Jova).
- A construção passo a passo da árvore **já existe** na literatura (árvore de derivação em Graciano Junior et al., 2022; árvore concreta, só parsers ascendentes, no VAST de Almeida-Martínez et al., 2009). Portanto, não é diferencial isolado.
- Nenhuma ferramenta da base descreve o formato das mensagens de erro nem avalia sua eficácia; o método usado no plano de avaliação vem de Marceau, Fisler e Krishnamurthi (2011), que não trata de compiladores.
- Nenhuma fonte relata acessibilidade; só um trabalho visa celulares, sem avaliação.

**Diferencial pretendido (não demonstrado):** integrar, em uma interface web executável com Docker Compose, as análises léxica e sintática (e, na Etapa 5, semântica) de um subconjunto documentado de C, com AST abstrata navegável ligada ao código, à regra gramatical e aos tokens, e mensagens de erro separadas por fase (encontrado, esperado, regra, dica), avaliadas por critérios definidos antes da coleta (C12–C16).

## 8. Limitações e ameaças à validade

- **Sem avaliação com estudantes até aqui:** a avaliação por pares está planejada (C12–C16, `avaliacao/formulario.md`); mesmo depois dela, não haverá evidência de ganho de aprendizagem, apenas de usabilidade, percepção e eficácia das mensagens.
- Erros no início de uma instrução (por exemplo, `10 = x;` ou `;` sozinho) trazem `regra = null`; nos demais, a regra EBNF violada é informada (observado em 13/11/2026).
- Subconjunto de C pequeno; recuperação de erros heurística.
- Celular **emulado**, não testado em aparelho real; navegador de teste apenas Chromium.
- Os testes foram escritos com apoio de IA e **revisados** contra a gramática (não contra o comportamento do código): vários erros de expectativa dos próprios testes foram encontrados e corrigidos (listados em `testes.md`).
- A análise semântica (Etapa 5) ainda não existe: o sistema aceita programas semanticamente incorretos (variável não declarada, tipos incompatíveis).
