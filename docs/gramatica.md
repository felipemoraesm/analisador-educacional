# Gramática do subconjunto de C (Etapa 4)

A gramática abaixo define **tudo** o que o parser reconhece. Ela é coerente com o scanner da Etapa 3: cada terminal é uma categoria de token (ou um lexema fixo) que o scanner produz. Esta é a mesma gramática servida por `GET /api/gramatica` e mostrada na tela; o teste `backend/tests/test_gramatica.py` garante que este arquivo e o código não divergem.

## 1. Gramática formal (EBNF)

Notação: `{ x }` = zero ou mais vezes; `[ x ]` = opcional; `|` = alternativa; `"lexema"` = terminal fixo; `MAIÚSCULAS` = categoria de token do scanner.

```ebnf
programa         = { definicao_funcao | declaracao | comando } ;

definicao_funcao = tipo_retorno IDENTIFICADOR "(" [ parametros ] ")" bloco ;
tipo_retorno     = "int" | "float" | "char" | "void" ;
parametros       = parametro { "," parametro } ;
parametro        = tipo IDENTIFICADOR ;
tipo             = "int" | "float" | "char" ;

declaracao       = tipo IDENTIFICADOR [ "=" expressao ] ";" ;

comando          = atribuicao | chamada_comando | condicional
                 | repeticao | retorno | bloco ;
atribuicao       = IDENTIFICADOR "=" expressao ";" ;
chamada_comando  = chamada ";" ;
condicional      = "if" "(" expressao ")" comando [ "else" comando ] ;
repeticao        = "while" "(" expressao ")" comando ;
retorno          = "return" [ expressao ] ";" ;
bloco            = "{" { declaracao | comando } "}" ;

expressao        = ou ;
ou               = e { "||" e } ;
e                = igualdade { "&&" igualdade } ;
igualdade        = relacional { ( "==" | "!=" ) relacional } ;
relacional       = soma { ( "<" | ">" | "<=" | ">=" ) soma } ;
soma             = termo { ( "+" | "-" ) termo } ;
termo            = unario { ( "*" | "/" | "%" ) unario } ;
unario           = ( "!" | "-" ) unario | primario ;
primario         = IDENTIFICADOR | chamada | LITERAL_INTEIRO | LITERAL_REAL
                 | LITERAL_STRING | LITERAL_CHAR | "(" expressao ")" ;
chamada          = IDENTIFICADOR "(" [ argumentos ] ")" ;
argumentos       = expressao { "," expressao } ;
```

- **Símbolo inicial:** `programa`.
- **Não terminais (25):** `programa`, `definicao_funcao`, `tipo_retorno`, `parametros`, `parametro`, `tipo`, `declaracao`, `comando`, `atribuicao`, `chamada_comando`, `condicional`, `repeticao`, `retorno`, `bloco`, `expressao`, `ou`, `e`, `igualdade`, `relacional`, `soma`, `termo`, `unario`, `primario`, `chamada`, `argumentos`.
- **Terminais:** os da tabela da seção 2.

## 2. Terminais e categorias de token do scanner

| Terminal na gramática | Categoria de token (Etapa 3) |
|---|---|
| `IDENTIFICADOR` | `IDENTIFICADOR` |
| `LITERAL_INTEIRO`, `LITERAL_REAL`, `LITERAL_STRING`, `LITERAL_CHAR` | as categorias de mesmo nome |
| `"int"` `"float"` `"char"` `"void"` `"if"` `"else"` `"while"` `"return"` | `PALAVRA_RESERVADA` |
| `"+"` `"-"` `"*"` `"/"` `"%"` | `OPERADOR_ARITMETICO` |
| `"=="` `"!="` `"<"` `">"` `"<="` `">="` | `OPERADOR_RELACIONAL` |
| `"&&"` `"||"` `"!"` | `OPERADOR_LOGICO` |
| `"="` | `OPERADOR_ATRIBUICAO` |
| `"("` `")"` `"{"` `"}"` `";"` `","` | `DELIMITADOR` |

Comentários e espaços não chegam ao parser (o scanner os descarta).

### Alteração feita no scanner para esta etapa

Para permitir funções que não devolvem valor, a palavra reservada **`void`** foi acrescentada ao scanner. Também foram acrescentados aos tokens os campos `fim_linha` e `fim_coluna`, que o parser usa para registrar o trecho de cada nó. Ambas as mudanças são aditivas: os testes léxicos foram atualizados de propósito (o conjunto de palavras reservadas e o formato exato do token) e a decisão está registrada em `docs/testes.md`.

## 3. Precedência e associatividade

Do **menor** para o **maior** nível (cada nível é uma regra da gramática, e é essa estrutura que produz a precedência):

| Nível | Operadores | Associatividade | Regra |
|---|---|---|---|
| 1 | `||` | esquerda | `ou` |
| 2 | `&&` | esquerda | `e` |
| 3 | `==` `!=` | esquerda | `igualdade` |
| 4 | `<` `>` `<=` `>=` | esquerda | `relacional` |
| 5 | `+` `-` | esquerda | `soma` |
| 6 | `*` `/` `%` | esquerda | `termo` |
| 7 | `!` `-` (unários) | direita | `unario` |

Exemplos (verificados pelos testes):

| Código | Agrupamento | Por quê |
|---|---|---|
| `10 + 5 * 2` | `10 + (5 * 2)` | `*` tem precedência maior que `+` |
| `20 - 5 - 3` | `(20 - 5) - 3` | `-` associa à esquerda |
| `(10 + 5) * 2` | `(10 + 5) * 2` | parênteses forçam o agrupamento |
| `a || b && c` | `a || (b && c)` | `&&` antes de `||` |
| `-a * b` | `(-a) * b` | unário antes de `*` |
| `- - a` | `-(-a)` | unários associam à direita |

## 4. Construções suportadas e fora do escopo

**Suportado:** declaração de variável (com valor inicial opcional); atribuição; expressões aritméticas, relacionais e lógicas com literais, variáveis, chamadas e parênteses; `if`/`else` (inclusive `else if`); `while`; `return` (com ou sem valor); blocos aninhados; definição de funções com parâmetros; chamadas de função (como comando e como expressão).

**Decisões de projeto (simplificações):**

- O programa é uma sequência de itens (`definicao_funcao | declaracao | comando`); portanto, comandos no nível global (como `x = 1;` ou `return 0;`) são aceitos. Verificar se faz sentido (por exemplo, `return` fora de função) é tarefa da análise semântica (Etapa 5).
- O corpo de `if` e `while` é um `comando`, com ou sem chaves. Uma **declaração** diretamente no corpo (`if (x) int y = 1;`) é erro: precisa estar em um bloco.
- **`else` casa com o `if` mais próximo** (resolve a ambiguidade do "else pendente").
- Uma atribuição é um **comando**, e não uma expressão (`a = b = 1;` não é aceito).
- Os parênteses de agrupamento **não viram nós** da AST, mas o trecho do nó os inclui.

**Fora do escopo:** arrays e colchetes (o scanner os reconhece, mas a gramática não os usa), ponteiros, `for`, `do`, `switch`, protótipos de função (declaração sem corpo), funções dentro de funções ou blocos, `void` como tipo de variável ou de parâmetro, expressões soltas como comando (`a + b;`), instrução vazia (`;`), operadores `++`/`--`/`+=`, operador ternário e pré-processador.

**Classe da gramática:** é uma gramática **LL(1) com pequenas exceções de lookahead**: para decidir entre `atribuicao` e `chamada_comando` olha-se o token seguinte ao identificador (`=` ou `(`), e para distinguir `declaracao` de `definicao_funcao` olha-se `tipo IDENTIFICADOR "("`. A recursão à esquerda das expressões foi eliminada com as repetições `{ }`, que também fixam a associatividade à esquerda.

## 5. Árvore de derivação × AST

| | Árvore de derivação (concreta) | AST (abstrata) |
|---|---|---|
| O que mostra | todas as regras aplicadas, com terminais e não terminais | só o que importa para o significado |
| Parênteses, `;`, `=` e palavras-chave | aparecem como folhas | são omitidos (ficam nos atributos) |
| Cadeias de regras (`expressao` → `ou` → `e` → ... → `primario`) | aparecem | são colapsadas |
| Esta ferramenta exibe | não | **sim** (rotulada como AST) |

Para `int x = 5 + 3;`:

```text
Árvore de derivação (resumida)            AST (o que a ferramenta mostra)
programa                                  PROGRAMA
└── declaracao                            └── DECLARACAO_VARIAVEL (tipo_dado=int, nome=x)
    ├── tipo → "int"                          └── ADICAO (operador=+)
    ├── IDENTIFICADOR "x"                         ├── LITERAL_INTEIRO (valor=5)
    ├── "="                                       └── LITERAL_INTEIRO (valor=3)
    ├── expressao → ou → e → igualdade
    │   → relacional → soma
    │       ├── termo → unario → primario → 5
    │       ├── "+"
    │       └── termo → unario → primario → 3
    └── ";"
```

## 6. Exemplos de programas

### Válidos

```c
int resultado = 10 + 5 * 2;
```
AST: `DECLARACAO_VARIAVEL(resultado)` → `ADICAO(10, MULTIPLICACAO(5, 2))`.

```c
int soma(int a, int b) { return a + b; }
int r = soma(1, 2);
```
AST: `DEFINICAO_FUNCAO(soma)` com dois `PARAMETRO` e um `BLOCO`; `DECLARACAO_VARIAVEL(r)` com `CHAMADA_FUNCAO(soma)`.

```c
if (a > 0) { b = 1; } else { b = 2; }
```
AST: `CONDICIONAL(tem_senao=true)` com `condicao` (`COMPARACAO`), `entao` e `senao` (`BLOCO`).

### Inválidos (erros sintáticos intencionais)

| Código | Erro reportado | Regra violada |
|---|---|---|
| `int numero = 10}` | linha 1, coluna 16: era esperado `;` ao final da declaração, mas foi encontrado `}` | `declaracao` |
| `if (x > 0 { y = 1; }` | linha 1, coluna 11: era esperado `)` para fechar a condição do if, mas foi encontrado `{` | `condicional` |
| `int y = x + ;` | era esperada uma expressão depois do operador `+`, mas foi encontrado `;` | `primario` |
| `int x = 1 + * 2;` | operadores consecutivos: depois de `+` era esperado um operando | `primario` |
| `else { x = 1; }` | `else` sem `if` correspondente | `condicional` |
| `int while = 5;` | `while` é palavra reservada e não pode ser usada como nome | `declaracao` |
| `{ int x = 1;` | o código terminou antes de o bloco aberto na linha 1 ser fechado com `}` | `bloco` |
| `int f(int a);` | era esperado `{` para iniciar o corpo da função (protótipos não são suportados) | `definicao_funcao` |

## 7. Tratamento de erros

- **Mensagens** em português, com o que foi encontrado, o que era esperado (`esperado`), a regra EBNF violada (`regra`) e uma dica de correção quando cabe.
- **Recuperação (modo pânico):** após um erro, o parser descarta tokens até um ponto seguro (`;`, `}` ou o início de uma instrução) e continua, **acumulando até 10 erros**. Quando o `;` foi apenas esquecido no fim da linha, a próxima instrução não é descartada.
- **Sem cascata:** um `else` órfão causado por um `if` com erro não gera um segundo erro; a palavra reservada que causou o erro não reinicia a análise; o fim do código é reportado uma única vez (vários blocos abertos geram uma só mensagem).
- **Erros léxicos:** se o scanner encontrar qualquer erro léxico, o **parser não é executado**, porque tokens inválidos produziriam diagnósticos sintáticos enganosos. Os erros léxicos continuam sendo exibidos, e a resposta explica o motivo (`sintatico.motivo`).
- **Limites:** no máximo 40 níveis de aninhamento (parênteses, blocos, operadores unários) e 120 níveis de altura da árvore; acima disso o parser devolve um erro claro, e não uma falha.
