# O scanner (Etapa 3)

## Onde está e por que foi feito assim

| Item | Decisão |
|---|---|
| Código | `backend/app/scanner.py` (função `tokenizar`), integrado ao endpoint `POST /api/analisar` |
| Tecnologia | Python puro, **escrito à mão**, sem geradores (Flex/Ply/regex gigante) e sem dependências novas |
| Justificativa | Escrever o autômato à mão deixa explícitos os **estados** e as **transições**, que o frontend mostra no passo a passo. Geradores esconderiam isso. Também evita novas dependências no Docker |
| Estrutura | Um laço principal escolhe o reconhecedor pelo primeiro caractere (`_ident`, `_numero`, `_string`, `_caractere`, `_barra`, `_operador_composto`, `_desconhecido`) e cada um devolve onde o lexema termina |
| Complexidade | Uma única passada: O(n) no tamanho do código (limite de 20.000 caracteres) |

## Os autômatos

Identificador (palavras reservadas são identificadores confirmados em uma tabela):

```
        letra ou _              letra, dígito ou _
 (q0) ---------------> ((q1)) <--------------------+
                          \_________________________/
```

Números (`INT`, `REAL_PONTO`, `REAL`; qualquer outro caminho cai em `ERRO`, que é absorvente):

```
 (q0) --dígito--> ((INT)) --ponto--> (REAL_PONTO) --dígito--> ((REAL))
                    ^  \dígito          \outro => ERRO         ^ \dígito
                    +---+                                      +--+
```

Operadores compostos usam estados como `MENOR` → `MENOR_IGUAL`; strings usam `STRING`, `STRING_ESC` e `STRING_FIM`; caracteres usam `CHAR_ABRE`, `CHAR_CONTEUDO`, `CHAR_ESC` e `CHAR_FECHA`.

## O que cada token carrega

```json
{
  "tipo": "IDENTIFICADOR",
  "lexema": "numero",
  "linha": 1, "coluna": 5,
  "inicio": 4, "fim": 10,
  "caminho": [
    { "c": "n", "classe": "letra", "estado": "IDENT" },
    { "c": "u", "classe": "letra", "estado": "IDENT" }
  ]
}
```

`caminho` tem um item por caractere consumido: é o que alimenta o **passo a passo** (a interface mostra o caractere, sua classe e o estado do autômato). Em erros, o último estado é `ERRO`. Lexemas com mais de 40 caracteres são truncados com `…` na exibição; `inicio` e `fim` continuam exatos.

## Contrato da API

`POST /api/analisar` com `{"codigo": "<texto>"}`. As validações da Etapa 2 (vazio, só espaços, tamanho, JSON inválido) vêm **antes** do scanner e continuam iguais (HTTP 400/413).

**Resposta (HTTP 200)** para qualquer código válido como entrada, **inclusive com erros léxicos** (a análise foi feita; os erros são resultado, não requisição inválida):

| Campo | Tipo | Descrição |
|---|---|---|
| `recebido` | bool | sempre `true` (mantido da Etapa 2) |
| `sucesso` | bool | `true` se **não** houve erro léxico |
| `mensagem` | string | ex.: `"Análise léxica concluída: 5 tokens, nenhum erro léxico."` |
| `linhas`, `caracteres` | int | tamanho da entrada |
| `tokens` | lista | tokens na ordem do código |
| `erros` | lista | erros léxicos (`tipo: "ERRO_LEXICO"`, `lexema`, `linha`, `coluna`, `inicio`, `fim`, `mensagem`, `dica`, `caminho`) |
| `comentarios` | lista | comentários ignorados (`tipo`, `lexema`, `linha`, `coluna`, `inicio`, `fim`) |
| `resumo` | objeto | `total_tokens`, `total_erros`, `total_comentarios`, `por_categoria` |

Exemplo (resumido) para `int a = @;`:

```json
{
  "recebido": true,
  "sucesso": false,
  "mensagem": "Análise léxica concluída: 4 tokens e 1 erro léxico.",
  "tokens": [
    { "tipo": "PALAVRA_RESERVADA", "lexema": "int", "linha": 1, "coluna": 1 },
    { "tipo": "IDENTIFICADOR", "lexema": "a", "linha": 1, "coluna": 5 },
    { "tipo": "OPERADOR_ATRIBUICAO", "lexema": "=", "linha": 1, "coluna": 7 },
    { "tipo": "DELIMITADOR", "lexema": ";", "linha": 1, "coluna": 10 }
  ],
  "erros": [
    { "tipo": "ERRO_LEXICO", "lexema": "@", "linha": 1, "coluna": 9,
      "mensagem": "Caractere não reconhecido: '@'",
      "dica": "Verifique se ele faz parte do subconjunto suportado." }
  ],
  "comentarios": [],
  "resumo": { "total_tokens": 4, "total_erros": 1, "total_comentarios": 0,
              "por_categoria": { "PALAVRA_RESERVADA": 1, "IDENTIFICADOR": 1,
                                 "OPERADOR_ATRIBUICAO": 1, "DELIMITADOR": 1 } }
}
```

(Os campos `inicio`, `fim` e `caminho` foram omitidos por brevidade.)

## Mudança intencional em relação à Etapa 2

A mensagem de sucesso deixou de ser `"Código recebido com sucesso."` e passou a descrever a análise léxica. Os campos `recebido`, `linhas` e `caracteres` foram **mantidos**. Dois testes (um do backend e um da interface) foram atualizados de propósito e isso está registrado em `docs/testes.md`.

## Limitações

- Só há análise léxica: programas com erros sintáticos ou semânticos são tokenizados normalmente (o `if (x ;` gera tokens válidos).
- Não há pré-processador, hexadecimal, notação científica, sufixos numéricos nem `for`/`void` (ver `docs/escopo-lexico.md`).
- Letras acentuadas fora de strings e comentários são erro léxico (identificadores são ASCII).
- Uma string ou caractere não fechado é consumido até o fim da linha; um comentário de bloco não fechado consome o restante do código.
