# Casos de teste (Etapa 4)

> Arquivo gerado por `scripts/gerar_casos.py` a partir de
> `backend/tests/casos/casos_artigo.json`. **Não edite à mão**: altere o JSON e gere de novo.

Os resultados esperados foram escritos a partir da gramática (`docs/gramatica.md`) e do
roteiro da disciplina, e são executados contra a API real por
`backend/tests/test_casos_artigo.py`. Se algum resultado esperado precisar mudar,
registre a mudança e o motivo na seção "Mudanças nos casos" no fim deste arquivo.

**Notação da AST de referência:** (PROGRAMA ...), (FUNCAO tipo nome (PARAM tipo nome)... corpo), (DECL tipo nome [valor]), (ATRIB nome valor), (SE cond entao [senao]), (ENQUANTO cond corpo), (BLOCO ...), (RETORNO [valor]), (CHAMADA nome args...), (op esq dir) para binárias, (neg x) e (! x) para unárias; identificadores e literais como no código.

Coluna "Verificação": *automatizado* = `backend/tests/test_casos_artigo.py`; *Etapa 5* = depende
da análise semântica (marcado como *skipped*); demais casos indicam o teste ou a verificação manual.
Execução de 13/11/2026: 68 aprovados, 0 reprovados, 7 ignorados (Etapa 5).
Os critérios (C1 a C18) estão em `docs/materiais-e-metodos.md`.



## Válido

| ID | Entrada (⏎ = quebra de linha) | Resultado esperado | AST de referência | Análise | Critérios | Verificação |
|---|---|---|---|---|---|---|
| CT-V01 | `int x;` | Declaração sem valor inicial. | `(PROGRAMA (DECL int x))` | Léxica e sintática | C1 | automatizado |
| CT-V02 | `int numero = 10;` | Declaração com valor inicial. | `(PROGRAMA (DECL int numero 10))` | Léxica e sintática | C1 | automatizado |
| CT-V03 | `float media = 7.5;⏎char letra = 'A';` | Tipos float e char. | `(PROGRAMA (DECL float media 7.5) (DECL char letra 'A'))` | Léxica e sintática | C1 | automatizado |
| CT-V04 | `int x;⏎x = 5;` | Atribuição simples. | `(PROGRAMA (DECL int x) (ATRIB x 5))` | Léxica e sintática | C1 | automatizado |
| CT-V05 | `int resultado = 10 + 5 * 2;` | * abaixo de + (precedência). | `(PROGRAMA (DECL int resultado (+ 10 (* 5 2))))` | Léxica e sintática | C1, C3 | automatizado |
| CT-V06 | `int r = 20 - 5 - 3;` | Associatividade à esquerda. | `(PROGRAMA (DECL int r (- (- 20 5) 3)))` | Léxica e sintática | C1, C3 | automatizado |
| CT-V07 | `int r = (10 + 5) * 2;` | Parênteses mudam a árvore e não viram nó. | `(PROGRAMA (DECL int r (* (+ 10 5) 2)))` | Léxica e sintática | C1, C3 | automatizado |
| CT-V08 | `r = -a * b;` | Unário antes de *. | `(PROGRAMA (ATRIB r (* (neg a) b)))` | Léxica e sintática | C1, C3 | automatizado |
| CT-V09 | `r = a < b && b != 0 \|\| !c;` | relacional > igualdade > && > \|\|. | `(PROGRAMA (ATRIB r (\|\| (&& (< a b) (!= b 0)) (! c))))` | Léxica e sintática | C1, C3 | automatizado |
| CT-V10 | `x = - - a;` | Unários associam à direita. | `(PROGRAMA (ATRIB x (neg (neg a))))` | Léxica e sintática | C1, C3 | automatizado |
| CT-V11 | `if (x > 0) { x = x - 1; }` | if sem else, com bloco. | `(PROGRAMA (SE (> x 0) (BLOCO (ATRIB x (- x 1)))))` | Léxica e sintática | C1 | automatizado |
| CT-V12 | `if (x == 0) y = 1; else y = 2;` | if-else sem chaves. | `(PROGRAMA (SE (== x 0) (ATRIB y 1) (ATRIB y 2)))` | Léxica e sintática | C1 | automatizado |
| CT-V13 | `if (a) if (b) x = 1; else x = 2;` | else pendente ligado ao if interno. | `(PROGRAMA (SE a (SE b (ATRIB x 1) (ATRIB x 2))))` | Léxica e sintática | C1 | automatizado |
| CT-V14 | `if (a) x = 1; else if (b) x = 2; else x = 3;` | else if. | `(PROGRAMA (SE a (ATRIB x 1) (SE b (ATRIB x 2) (ATRIB x 3))))` | Léxica e sintática | C1 | automatizado |
| CT-V15 | `while (i < 10) { i = i + 1; }` | Repetição while. | `(PROGRAMA (ENQUANTO (< i 10) (BLOCO (ATRIB i (+ i 1)))))` | Léxica e sintática | C1 | automatizado |
| CT-V16 | `{ int y; { y = 1; } }` | Blocos aninhados. | `(PROGRAMA (BLOCO (DECL int y) (BLOCO (ATRIB y 1))))` | Léxica e sintática | C1 | automatizado |
| CT-V17 | `int soma(int a, int b) { return a + b; }⏎int r = soma(1, 2);` | Função com parâmetros, return e chamada como expressão. | `(PROGRAMA (FUNCAO int soma (PARAM int a) (PARAM int b) (BLOCO (RETORNO (+ a b)))) (DECL int r (CHAMADA soma 1 2)))` | Léxica e sintática | C1 | automatizado |
| CT-V18 | `void f() { g(1, h(2)); return; }` | void, chamada como comando, chamada aninhada, return sem valor. | `(PROGRAMA (FUNCAO void f (BLOCO (CHAMADA g 1 (CHAMADA h 2)) (RETORNO))))` | Léxica e sintática | C1 | automatizado |
| CT-V19 | `char s = "oi";` | Literal de cadeia como valor (aceito pela gramática; tipos só na Etapa 5). | `(PROGRAMA (DECL char s "oi"))` | Léxica e sintática | C1 | automatizado |
| CT-V20 | `return 0;` | return no nível global é aceito pela sintaxe (decisão de projeto; verificado na Etapa 5). | `(PROGRAMA (RETORNO 0))` | Léxica e sintática | C1 | automatizado |
| CT-V21 | `Exemplo 4 da interface` | if/else com comentário: comentário fora da AST. | `(PROGRAMA (DECL int valor 0) (DECL int resposta) (SE (== valor 0) (BLOCO (ATRIB resposta 1)) (BLOCO (ATRIB resposta 2))))` | Léxica e sintática | C1 | automatizado |

## Erro léxico

| ID | Entrada (⏎ = quebra de linha) | Resultado esperado | AST de referência | Análise | Critérios | Verificação |
|---|---|---|---|---|---|---|
| CT-L01 | `int a = @;` | Erro léxico '@' em L1 C9; parser não executado. | — | Léxica | C2, C4 | automatizado |
| CT-L02 | `float t = 3.;` | Literal real malformado '3.' em L1 C11; parser não executado. | — | Léxica | C2, C4 | automatizado |
| CT-L03 | `int x; /* sem fim` | Comentário de bloco não fechado em L1 C8. | — | Léxica | C2, C4 | automatizado |
| CT-L04 | `int 2x = 5;` | '2x': identificador não pode começar com dígito (L1 C5). | — | Léxica | C2, C4 | automatizado |
| CT-L05 | `if (a & b) x = 1;` | '&' sozinho em L1 C7, com dica para usar &&. | — | Léxica | C2, C4 | automatizado |
| CT-L06 | `int ação = 1;` | Dois erros: 'ç' (L1 C6) e 'ã' (L1 C7). | — | Léxica | C2, C4 | automatizado |
| CT-L07 | `char c = 'ab';` | Literal de caractere com mais de um caractere (L1 C10). | — | Léxica | C2, C4 | automatizado |
| CT-L08 | `Exemplo 8 da interface` | 8 erros léxicos; parser não executado. | — | Léxica | C2, C4 | automatizado |

## Erro sintático

| ID | Entrada (⏎ = quebra de linha) | Resultado esperado | AST de referência | Análise | Critérios | Verificação |
|---|---|---|---|---|---|---|
| CT-S01 | `int numero = 10}` | Esperado ';', encontrado '}' em L1 C16 (caso do roteiro). | — | Sintática | C2, C4 | automatizado |
| CT-S02 | `int x = 10⏎int y;` | Falta ';': esperado ';', encontrado 'int' em L2 C1. | — | Sintática | C2, C4 | automatizado |
| CT-S03 | `if (x > 0 { x = 1; }` | Falta ')': encontrado '{' em L1 C11. | — | Sintática | C2, C4 | automatizado |
| CT-S04 | `while (x) { x = 0;` | Falta '}': fim do código em L1 C19. | — | Sintática | C2, C4 | automatizado |
| CT-S05 | `y = x + ;` | Expressão sem operando: encontrado ';' em L1 C9. | — | Sintática | C2, C4 | automatizado |
| CT-S06 | `x = a * / b;` | Operadores consecutivos: encontrado '/' em L1 C9. | — | Sintática | C2, C4 | automatizado |
| CT-S07 | `else x = 1;` | 'else' sem 'if' em L1 C1. | — | Sintática | C2, C4 | automatizado |
| CT-S08 | `int while = 5;` | Palavra reservada no lugar de nome (L1 C5); 1 erro, sem cascata. | — | Sintática | C2, C4 | automatizado |
| CT-S09 | `int x =` | Fim inesperado: esperada expressão, encontrado fim do código (L1 C8). | — | Sintática | C2, C4 | automatizado |
| CT-S10 | `10 = x;` | Instrução não pode começar com literal (L1 C1). | — | Sintática | C2, C4 | automatizado |
| CT-S11 | `;` | Instrução vazia não suportada (L1 C1). | — | Sintática | C2, C4 | automatizado |
| CT-S12 | `a + b;` | Expressão solta como instrução não é suportada (L1 C3). | — | Sintática | C2, C4 | automatizado |
| CT-S13 | `int v[3];` | Colchetes (arrays) fora do escopo (L1 C6). | — | Sintática | C2, C4 | automatizado |
| CT-S14 | `int a, b;` | Declaração múltipla não suportada (L1 C6). | — | Sintática | C2, C4 | automatizado |
| CT-S15 | `if x > 0 { }` | Esperado '(' após 'if', encontrado 'x' (L1 C4). | — | Sintática | C2, C4 | automatizado |
| CT-S16 | `if (x) int y = 1;` | Declaração no corpo do if sem chaves (L1 C8). | — | Sintática | C2, C4 | automatizado |
| CT-S17 | `int f(int a);` | Protótipo não suportado: esperado '{' (L1 C13). | — | Sintática | C2, C4 | automatizado |
| CT-S18 | `int f(int a, b) { }` | Parâmetro sem tipo (L1 C14). | — | Sintática | C2, C4 | automatizado |
| CT-S19 | `void v;` | void fora de lugar: só é aceito como tipo de retorno. | — | Sintática | C2, C4 | automatizado |
| CT-S20 | `int a = ;⏎int b = 2⏎b = 3;` | Recuperação: 2 erros (L1 C9 e L3 C1); a linha 3 é reconhecida. | — | Sintática | C2, C4 | automatizado |
| CT-S21 | `if (x > 0 { y = 1; } else { y = 2; }` | Anti-cascata: só 1 erro (L1 C11); o else não gera outro. | — | Sintática | C2, C4 | automatizado |
| CT-S22 | `{⏎  { int x = 1;` | Dois blocos abertos, uma única mensagem de fim (L2 C15). | — | Sintática | C2, C4 | automatizado |
| CT-S23 | `Exemplo 5 da interface` | Tokens válidos; 2 erros (L2 C1 e L2 C13); 'z = 5;' é aceito pela sintaxe. | — | Sintática | C2, C4 | automatizado |

## Erro semântico

| ID | Entrada (⏎ = quebra de linha) | Resultado esperado | AST de referência | Análise | Critérios | Verificação |
|---|---|---|---|---|---|---|
| CT-SE01 | `z = 5;` | Identificador 'z' não declarado. | — | Semântica | C11 | Etapa 5 (previsto) |
| CT-SE02 | `int x;⏎int x;` | Redeclaração de 'x' no mesmo escopo. | — | Semântica | C11 | Etapa 5 (previsto) |
| CT-SE03 | `{ int y = 1; }⏎y = 2;` | 'y' usado fora do escopo. | — | Semântica | C11 | Etapa 5 (previsto) |
| CT-SE04 | `x = 1;⏎int x;` | 'x' usado antes da declaração. | — | Semântica | C11 | Etapa 5 (previsto) |

## Aviso semântico

| ID | Entrada (⏎ = quebra de linha) | Resultado esperado | AST de referência | Análise | Critérios | Verificação |
|---|---|---|---|---|---|---|
| CT-SE05 | `int i = 3.7;` | Aviso (não erro): conversão implícita de float para int. | — | Semântica | C11 | Etapa 5 (previsto) |

## Erro semântico

| ID | Entrada (⏎ = quebra de linha) | Resultado esperado | AST de referência | Análise | Critérios | Verificação |
|---|---|---|---|---|---|---|
| CT-SE06 | `return 0;` | return fora de função (aceito pela sintaxe; CT-V20). | — | Semântica | C11 | Etapa 5 (previsto) |
| CT-SE07 | `int f(int a) { return a; }⏎int r = f(1, 2);` | Número de argumentos diferente do de parâmetros. | — | Semântica | C11 | Etapa 5 (previsto) |

## Borda

| ID | Entrada (⏎ = quebra de linha) | Resultado esperado | AST de referência | Análise | Critérios | Verificação |
|---|---|---|---|---|---|---|
| CT-B01 | `(campo vazio)` | Frontend: mensagem sem chamar a API; backend: 400 codigo_vazio. | — | Validação | C2 | automatizado |
| CT-B02 | `(apenas espaços e quebras de linha)` | 400 codigo_somente_espacos. | — | Validação | C2 | automatizado |
| CT-B03 | `// nada⏎/* nada */` | 0 tokens e 2 comentários; programa vazio válido: PROGRAMA sem filhos. | `(PROGRAMA)` | Sintática | C1 | automatizado |
| CT-B04 | `x = 1;` | Programa com um único comando. | `(PROGRAMA (ATRIB x 1))` | Sintática | C1 | automatizado |
| CT-B05 | `x = (((…(1)…))); com 40 níveis de parênteses` | Aceito (limite documentado: 40). | `(PROGRAMA (ATRIB x 1))` | Sintática | C5 | automatizado |
| CT-B06 | `o mesmo com 41 níveis` | Erro sintático 'aninhamento profundo demais'; HTTP 200, nunca 500. | — | Sintática | C5 | automatizado |
| CT-B07 | `código com 20.001 caracteres` | 413 codigo_muito_grande. | — | Validação | C2 | automatizado |
| CT-B08 | `int a = 1 @;⏎int b = 2;` | 1 erro léxico ('@', L1 C11); parser não executado (decisão de projeto). | — | Sintática | C2, C4 | automatizado |
| CT-B09 | `15 linhas com 'x = ;'` | 10 erros devolvidos e erros_truncados = true. | — | Sintática | C4, C5 | automatizado |
| CT-B10 | `programa válido com cerca de 19.000 caracteres` | Aceito em menos de 2 s no ambiente de testes. | — | Sintática | C8 | automatizado |
| CT-B11 | `JSON malformado ou sem o campo codigo` | 400 requisicao_invalida. | — | Validação | C2 | automatizado |
| CT-B12 | `x = 1;⏎	if (x) { y = 2; }` | Posições dos nós iguais às dos tokens com CRLF e tabulação. | — | Sintática | C6 | automatizado |

## Fluxo e interface

| ID | Entrada (⏎ = quebra de linha) | Resultado esperado | AST de referência | Análise | Critérios | Verificação |
|---|---|---|---|---|---|---|
| CT-F01 | `cada exemplo pronto (1 a 12)` | Exemplos 5, 8 e 12 com os erros esperados; os demais sem erros. | — | Fluxo completo | C1, C2 | automatizado |
| CT-F02 | `todos os casos válidos` | Folhas da AST coincidem com tokens (tipo, lexema, posição) e o trecho de cada nó contém o dos filhos. | — | Consistência | C6 | automatizado |
| CT-F03 | `construção passo a passo da AST: avançar até o fim e voltar` | Estados idênticos nos dois sentidos. | — | Interface | C6 | frontend/tests/sintatico_interface.test.js |
| CT-F04 | `resposta de /api/analisar` | Campos da Etapa 3 presentes, com os mesmos tipos e significados. | — | Contrato | C7 | automatizado |
| CT-F05 | `suítes das Etapas 1 a 3` | Todas continuam aprovadas. | — | Regressão | C7 | todas as suítes |
| CT-F06 | `AST e erros usados só com teclado` | Nós e controles alcançáveis por Tab; categorias por cor, símbolo e texto. | — | Interface | C17 | manual |
| CT-F07 | `interface em 360 px (emulação) e um celular real` | Sem rolagem horizontal; tarefas T1 a T4 executáveis. | — | Interface | C18 | tests/e2e (emulação) + manual |

## Registro de execução (preencher na Etapa 6)

| ID | Entrada utilizada | Resultado esperado | Resultado observado | Status (aprovado / reprovado / pendente) | Defeito identificado | Correção realizada |
|---|---|---|---|---|---|---|
| | | | | | | |

## Mudanças nos casos

| Data | Caso | Mudança | Justificativa |
|---|---|---|---|
| | | | |
