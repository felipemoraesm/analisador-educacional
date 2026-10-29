# Escopo léxico – subconjunto de C

Este documento define **tudo** o que o scanner reconhece. O que não está aqui é tratado como erro léxico. A análise léxica só classifica lexemas: **ela não verifica se o programa faz sentido** (isso é papel do parser, na Etapa 4).

## Categorias de token

| Categoria (`tipo`) | Regra de formação | Exemplos |
|---|---|---|
| `PALAVRA_RESERVADA` | `int` `float` `char` `if` `else` `while` `return` (lexema inteiro, com minúsculas) | `int`, `while` |
| `IDENTIFICADOR` | letra ASCII ou `_`, seguida de letras ASCII, dígitos ou `_` (e que não seja palavra reservada) | `numero`, `_x1`, `total2` |
| `LITERAL_INTEIRO` | um ou mais dígitos decimais | `0`, `42`, `007` |
| `LITERAL_REAL` | dígitos, ponto, dígitos (um único ponto) | `3.14`, `0.5` |
| `LITERAL_STRING` | `"` ... `"` na mesma linha, com escapes `\n \t \r \0 \\ \" \'` | `"ola\n"` |
| `LITERAL_CHAR` | `'` um caractere ou um escape `'` | `'a'`, `'\n'`, `'\''` |
| `OPERADOR_ARITMETICO` | `+` `-` `*` `/` `%` | `+`, `%` |
| `OPERADOR_RELACIONAL` | `==` `!=` `<` `>` `<=` `>=` | `<=` |
| `OPERADOR_LOGICO` | `&&` `\|\|` `!` | `&&` |
| `OPERADOR_ATRIBUICAO` | `=` | `=` |
| `DELIMITADOR` | `(` `)` `{` `}` `[` `]` `;` `,` | `;` |

## Itens descartados (não geram token)

| Item | Tratamento |
|---|---|
| Espaços, tabs, `\f`, `\v` | ignorados |
| Quebras de linha (`\n`, `\r\n`, `\r`) | ignoradas (apenas incrementam a linha) |
| Comentário de linha `// ...` | ignorado até o fim da linha; devolvido na lista `comentarios` |
| Comentário de bloco `/* ... */` | ignorado (pode ter várias linhas; **não aninha**); devolvido em `comentarios` |

## Regras de desempate (maior casamento)

O scanner sempre leva o **maior lexema possível** a partir da posição atual:

- `<=` é um token, e não `<` seguido de `=`; `a===b` vira `a`, `==`, `=`, `b`.
- `3.14` é um real, e não `3`, `.` e `14`.
- `intx` é um identificador, e não `int` seguido de `x`; `int` só é palavra reservada quando é o lexema inteiro.
- `//` e `/*` iniciam comentário; `/` sozinho é divisão.

## Posição

- `linha` e `coluna` começam em **1** e contam **caracteres** (um tab conta 1; um emoji conta 1).
- `\r\n`, `\n` e `\r` contam, cada um, como **uma** quebra de linha.
- `inicio` e `fim` são deslocamentos em **unidades UTF-16** (início inclusivo, fim exclusivo), para o frontend recortar a string do JavaScript sem erro, mesmo com emojis.

## Erros léxicos

O scanner **não para** no primeiro erro: registra, pula o trecho problemático e continua, para mostrar todos os problemas de uma vez.

| Situação | Lexema do erro | Mensagem (resumo) |
|---|---|---|
| Caractere fora do subconjunto (`@ $ # ~ ^ ? : \ \`` e outros) | o caractere | Caractere não reconhecido (`#` e `.` têm dicas próprias) |
| Caractere de controle ou espaço especial (ex.: U+00A0 ao colar da web) | o caractere | Caractere não reconhecido, com o código `U+XXXX` e dica |
| Letra acentuada (`ç`, `ã`...) | o caractere | Identificadores aceitam apenas letras sem acento |
| `&` ou `\|` sozinhos | o caractere | Dica: o operador é `&&` / `\|\|` |
| Real sem dígitos depois do ponto (`3.`) | `3.` | Faltam dígitos depois do ponto decimal |
| Número com mais de um ponto (`1.2.3`) | `1.2.3` | Um real tem apenas um ponto decimal |
| Número seguido de letras (`12abc`, `2x`) | `12abc` | Identificador não pode começar com dígito |
| Hexadecimal (`0x1F`) e notação científica (`1e5`) | o literal | Não fazem parte do subconjunto |
| String não fechada | da `"` até o fim da linha | Faltou a aspa de fechamento |
| Escape inválido (`"a\q"`, `'\q'`) | o literal | Sequência de escape inválida |
| Caractere vazio (`''`) ou com mais de um caractere (`'ab'`) | o literal | Mensagens específicas, com dica de usar string |
| Caractere não fechado (`'a`) | do `'` até o fim da linha | Faltou o apóstrofo de fechamento |
| Comentário de bloco não fechado | de `/*` até o fim do código | Faltou o `*/` (o restante foi consumido) |

## O que **não** faz parte do subconjunto (por enquanto)

Pré-processador (`#include`, `#define`), `for`, `do`, `switch`, `void`, `struct`, ponteiros e endereço (`*p`, `&x`), `++`/`--`, atribuições compostas (`+=`), operadores bit a bit, hexadecimal/octal, notação científica, sufixos (`10L`, `1.5f`) e strings com continuação de linha.

## Relação com as etapas seguintes

O escopo **léxico** é um pouco maior que o escopo **sintático** que será implementado: o parser (Etapa 4) poderá cobrir apenas parte dessas construções (por exemplo, declarações, expressões, `if/else`, `while` e `return`), mas o scanner já tokeniza todas elas.
