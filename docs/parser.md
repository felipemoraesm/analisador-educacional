# O parser e a AST (Etapa 4)

## 1. Estratégia, tecnologia e justificativa

| Item | Decisão |
|---|---|
| Estratégia | **Descendente recursivo** (*recursive descent*): cada não terminal da gramática é um método de `_Parser` (`declaracao`, `condicional`, `binaria`, `primario`...) |
| Código | `backend/app/parser.py` (parser e AST), `backend/app/gramatica.py` (gramática e metadados dos nós), `backend/app/analise.py` (integra scanner e parser na resposta) |
| Tecnologia | Python puro, **escrito à mão**; nenhuma biblioteca nova e nenhuma etapa de geração de código no build do Docker |
| Implementado à mão × gerado | **Tudo à mão**: scanner (Etapa 3), parser, construção da AST, mensagens e recuperação de erros. Nada é gerado por ferramenta |
| Por que descendente recursivo | É a estratégia mais didática: a regra EBNF e o método têm a mesma forma, o que permite mostrar ao estudante "qual regra o parser está usando" em cada nó e em cada erro. Também facilita mensagens específicas por contexto ("ao final da declaração", "para fechar a condição do if") |
| Por que não um gerador (ANTLR, PLY, Lark) | Esconderiam a estrutura que a ferramenta quer ensinar, adicionariam dependências e uma etapa de geração ao build, e tornariam mais difícil produzir diagnósticos com a regra violada |
| Por que não LL(1) com tabela ou LR | A tabela LL(1) exigiria FIRST/FOLLOW e fatoração explícitos; LR/LALR produz erros mais genéricos. Aqui a prioridade é explicar a estrutura e os erros |
| Vantagens | Código legível e testável por regra; precedência e associatividade vêm da própria estrutura (um método por nível); mensagens contextuais; sem dependências |
| Limitações | A recursão exige limites de aninhamento (40) e de altura (120) para não estourar a pilha; a recuperação de erros é heurística (modo pânico), não ótima; há lookahead extra de 1 a 2 tokens em dois pontos (ver `docs/gramatica.md`) |

## 2. Fluxo

```
código → validação (Etapa 2) → scanner (Etapa 3) → tokens
                                      │
                    há erro léxico? ──┼── sim → parser NÃO roda; erros léxicos são exibidos
                                      │
                                      └── não → parser → AST  (ou erros sintáticos, com AST nula)
```

O parser **reaproveita o scanner da Etapa 3 sem reimplementá-lo**: recebe a lista de tokens exatamente como a tabela de tokens da interface a mostra. O diagrama completo está em [`docs/fluxograma.md`](fluxograma.md).

### Decisão sobre erros léxicos

Quando o scanner encontra **qualquer erro léxico, o parser não é executado**. Justificativa: uma sequência de tokens com lacunas (um caractere ou literal inválido descartado) produziria erros sintáticos sem sentido, em cascata, que confundem o estudante. Os erros léxicos continuam sendo apresentados normalmente; a resposta traz `sintatico.executado = false`, `sintatico.sucesso = null` e o texto de `sintatico.motivo`, e a interface mostra "Análise sintática não executada" com a explicação. A decisão é verificada em testes do backend (o parser nem é chamado), da interface e de ponta a ponta.

### O que mudou no scanner

Duas mudanças aditivas, com os testes léxicos atualizados de propósito (ver `docs/testes.md`): a palavra reservada `void` e os campos `fim_linha`/`fim_coluna` em cada token. Fora isso, o scanner produz os mesmos tokens para as mesmas entradas (há testes de regressão).

## 3. A AST

### Formato do nó (JSON)

Todo nó segue o mesmo formato, e nós do mesmo tipo têm sempre os mesmos atributos:

```json
{
  "tipo": "DECLARACAO_VARIAVEL",
  "id": 2,
  "papel": "item",
  "linha": 1, "coluna": 1,
  "fim_linha": 1, "fim_coluna": 17,
  "inicio": 0, "fim": 16,
  "atributos": { "tipo_dado": "int", "nome": "numero" },
  "filhos": [ ... ]
}
```

| Campo | Significado |
|---|---|
| `tipo` | tipo do nó (tabela abaixo) |
| `id` | número do nó em **pré-ordem** (raiz = 1), usado para selecionar e animar na interface |
| `papel` | função do nó dentro do pai (`esquerda`, `direita`, `condicao`, `entao`, `senao`, `valor`, `argumento`, `corpo`...); `null` na raiz |
| `linha`, `coluna` | início do trecho (a partir de 1; conta caracteres) |
| `fim_linha`, `fim_coluna` | posição logo **após** o trecho |
| `inicio`, `fim` | deslocamentos do trecho em unidades UTF-16 (`codigo.slice(inicio, fim)` no JavaScript) |
| `atributos` | dados do nó (ver tabela) |
| `filhos` | nós filhos, na ordem do código |

O trecho de um nó **inclui os parênteses de agrupamento**, mas os parênteses não viram nós.

### Tipos de nó

| Tipo | Atributos | Filhos (papel) | Regra |
|---|---|---|---|
| `PROGRAMA` | – | `item`* (função, declaração ou comando) | `programa` |
| `DEFINICAO_FUNCAO` | `tipo_retorno`, `nome` | `parametro`* (`PARAMETRO`), `corpo` (`BLOCO`) | `definicao_funcao` |
| `PARAMETRO` | `tipo_dado`, `nome` | – | `parametro` |
| `BLOCO` | – | `instrucao`* | `bloco` |
| `DECLARACAO_VARIAVEL` | `tipo_dado`, `nome` | `valor` (opcional) | `declaracao` |
| `ATRIBUICAO` | `nome` | `valor` | `atribuicao` |
| `CONDICIONAL` | `tem_senao` (bool) | `condicao`, `entao`, `senao` (opcional) | `condicional` |
| `REPETICAO` | – | `condicao`, `corpo` | `repeticao` |
| `RETORNO` | – | `valor` (opcional) | `retorno` |
| `CHAMADA_FUNCAO` | `nome` | `argumento`* | `chamada` |
| `ADICAO` `SUBTRACAO` `MULTIPLICACAO` `DIVISAO` `MODULO` | `operador` | `esquerda`, `direita` | `soma`, `termo` |
| `COMPARACAO` | `operador` (`==` `!=` `<` `>` `<=` `>=`) | `esquerda`, `direita` | `igualdade`, `relacional` |
| `OPERACAO_LOGICA` | `operador` (`&&` `\|\|`) | `esquerda`, `direita` | `ou`, `e` |
| `NEGACAO_LOGICA` | `operador` (`!`) | `operando` | `unario` |
| `MENOS_UNARIO` | `operador` (`-`) | `operando` | `unario` |
| `IDENTIFICADOR` | `nome` | – | `primario` |
| `LITERAL_INTEIRO` `LITERAL_REAL` `LITERAL_STRING` `LITERAL_CHAR` | `valor` (texto exato do código) | – | `primario` |

Metadados de cada tipo (regra EBNF, descrição e categoria) vêm em `sintatico.regras` e em `GET /api/gramatica`.

### Exemplo: `int numero = 10;`

```json
{
  "tipo": "PROGRAMA",
  "id": 1,
  "papel": null,
  "linha": 1,
  "coluna": 1,
  "fim_linha": 1,
  "fim_coluna": 17,
  "inicio": 0,
  "fim": 16,
  "atributos": {},
  "filhos": [
    {
      "tipo": "DECLARACAO_VARIAVEL",
      "id": 2,
      "papel": "item",
      "linha": 1,
      "coluna": 1,
      "fim_linha": 1,
      "fim_coluna": 17,
      "inicio": 0,
      "fim": 16,
      "atributos": {
        "tipo_dado": "int",
        "nome": "numero"
      },
      "filhos": [
        {
          "tipo": "LITERAL_INTEIRO",
          "id": 3,
          "papel": "valor",
          "linha": 1,
          "coluna": 14,
          "fim_linha": 1,
          "fim_coluna": 16,
          "inicio": 13,
          "fim": 15,
          "atributos": {
            "valor": "10"
          },
          "filhos": []
        }
      ]
    }
  ]
}
```

### Exemplo: `int resultado = 10 + 5 * 2;`

```text
PROGRAMA  [1:1]
└── item: DECLARACAO_VARIAVEL (tipo_dado=int nome=resultado)  [1:1]
    └── valor: ADICAO (operador=+)  [1:17]
        ├── esquerda: LITERAL_INTEIRO (valor=10)  [1:17]
        └── direita: MULTIPLICACAO (operador=*)  [1:22]
            ├── esquerda: LITERAL_INTEIRO (valor=5)  [1:22]
            └── direita: LITERAL_INTEIRO (valor=2)  [1:26]
```

A multiplicação está **abaixo** da adição: é a precedência. A mesma árvore em texto é devolvida em `sintatico.texto` (apenas para árvores de até 1.000 nós).

## 4. Contrato da API

`POST /api/analisar` com `{"codigo": "<texto>"}`. As validações de entrada da Etapa 2 vêm antes (HTTP 400/413). Para qualquer código aceito, a resposta é **HTTP 200**, **mesmo com erros léxicos ou sintáticos** (a análise foi feita; os erros são o resultado).

**Campos da Etapa 3, preservados no nível superior:** `recebido`, `sucesso` (continua significando "sem erro **léxico**"), `mensagem`, `linhas`, `caracteres`, `tokens`, `erros`, `comentarios`, `resumo` (ver `docs/scanner.md`).

**Campos novos (Etapa 4):**

| Campo | Descrição |
|---|---|
| `lexico` | resultado léxico agrupado: `sucesso`, `tokens`, `erros`, `comentarios`, `resumo` (os mesmos dados do nível superior) |
| `sintatico.executado` | `false` quando há erros léxicos |
| `sintatico.sucesso` | `true`, `false` ou `null` (quando não executado) |
| `sintatico.mensagem` | resumo da análise sintática |
| `sintatico.motivo` | por que não foi executado (ou `null`) |
| `sintatico.ast` | a AST (raiz `PROGRAMA`) ou `null` |
| `sintatico.erros` | erros sintáticos (lista vazia se não houver) |
| `sintatico.erros_truncados` | `true` se o limite de 10 erros foi atingido |
| `sintatico.resumo` | `total_nos`, `altura`, `por_tipo` (ou `null`) |
| `sintatico.regras` | regra EBNF, descrição e categoria de cada tipo de nó presente |
| `sintatico.texto` | árvore em texto indentado (árvores pequenas) ou `null` |

### Erro sintático

Para `int numero = 10}`:

```json
{
  "tipo": "ERRO_SINTATICO",
  "linha": 1,
  "coluna": 16,
  "inicio": 15,
  "fim": 16,
  "encontrado": "}",
  "encontrado_tipo": "DELIMITADOR",
  "esperado": [
    ";"
  ],
  "mensagem": "Era esperado ';' ao final da declaração, mas foi encontrado '}'.",
  "regra": "declaracao = tipo IDENTIFICADOR [ \"=\" expressao ] \";\" ;",
  "dica": null
}
```

| Campo | Significado |
|---|---|
| `encontrado` / `encontrado_tipo` | o token encontrado e sua categoria (`FIM` no fim do código) |
| `esperado` | lista do que o parser esperava (lexemas ou categorias) |
| `mensagem` | frase em português |
| `regra` | a regra EBNF que estava sendo aplicada |
| `dica` | como corrigir (quando cabe) |

Na interface a mensagem aparece como: *"Erro sintático na linha 1, coluna 16: era esperado ';' ao final da declaração, mas foi encontrado '}'."*

## 5. Tratamento de erros

**Tipos de erro tratados:** token inesperado; `;`, `)` ou `}` faltando; expressão sem operando; operadores consecutivos; fim inesperado do código; bloco não fechado; `else` sem `if`; palavra reservada onde se esperava nome; `}` ou `)` sobrando; instrução vazia; declaração no corpo de `if`/`while` sem chaves; função dentro de bloco; protótipo de função; `void` fora de lugar; parâmetros e argumentos mal formados; colchetes (arrays); aninhamento e altura acima dos limites.

**Recuperação (modo pânico), com vários erros por análise.** Após um erro, o parser descarta tokens até `;`, `}` ou o início de uma instrução, e continua. Regras para **evitar erros em cascata**:

1. um `;` esquecido no fim da linha não faz o parser descartar a próxima instrução;
2. a palavra reservada que causou o erro não reinicia a análise (`int while = 5;` gera 1 erro, e não 2);
3. um `else` que sobra por causa de um `if` com erro não gera um segundo erro;
4. o fim do código é reportado uma única vez, mesmo com vários blocos abertos (uma mensagem lista as linhas);
5. no máximo 10 erros são devolvidos.

**Exemplos reais:**

`int x = 10` / `int y = x + ;` / `z = 5;` (2 erros; a terceira linha é reconhecida normalmente):

- linha 2, coluna 1: Era esperado ';' ao final da declaração, mas foi encontrada a palavra reservada 'int'.
- linha 2, coluna 13: Era esperada uma expressão depois do operador '+', mas foi encontrado ';'.

`if (x > 0 { y = 1; } else { y = 2; }` (1 erro, sem cascata no `else`):

- linha 1, coluna 11: Era esperado ')' para fechar a condição do if, mas foi encontrado '{'.

`{` / `  { int x = 1;` (2 blocos abertos, 1 mensagem):

- linha 2, coluna 15: O código terminou antes de 2 blocos abertos serem fechados com '}' (abertos nas linhas 1, 2).

## 6. Limites e segurança

| Limite | Valor | O que acontece ao exceder |
|---|---|---|
| Tamanho do código | 20.000 caracteres | HTTP 413 com mensagem (Etapa 2) |
| Erros sintáticos | 10 | a lista é cortada e `erros_truncados = true` |
| Aninhamento (parênteses, blocos, operadores unários) | 40 níveis | erro sintático claro, sem estourar a pilha |
| Altura da AST | 120 níveis | erro claro (cadeias com centenas de operadores) |
| Texto da árvore | até 1.000 nós | `sintatico.texto = null` (a árvore interativa e o JSON continuam disponíveis) |

Mensagens de erro nunca incluem detalhes internos. Caracteres Unicode inválidos (um *surrogate* isolado) são rejeitados na validação com uma mensagem clara; antes isso causava erro 500 (defeito descoberto nesta etapa e corrigido).

## 7. Visualização na interface

Árvore navegável (nós expansíveis, **Expandir/Recolher tudo**, **filtro por tipo**), **clique em um nó para destacar o trecho no código**, detalhes do nó (regra gramatical, atributos, posição e **tokens do nó**, o que relaciona a árvore à tabela de tokens), **construção passo a passo** (do mais interno para a raiz, com controles de avançar, voltar e reproduzir), versão em texto acessível e **exportação em JSON**. Categorias de nó são diferenciadas por cor **e** por símbolo e texto. Com erro sintático, o trecho problemático é marcado no código colorido e a árvore não é exibida.

## 8. Limitações conhecidas e relação com a Etapa 5

- A análise **semântica não está implementada**: variável não declarada (`z = 5;`), incompatibilidade de tipos e `return` fora de função são aceitos pelo parser e serão detectados na Etapa 5.
- A gramática é um **subconjunto** (ver `docs/gramatica.md`): sem arrays, ponteiros, `for`, protótipos nem expressões soltas como instrução.
- A recuperação de erros é heurística: em programas muito quebrados, a lista pode omitir problemas escondidos atrás de outros.
- A AST traz posições em cada nó e atributos consistentes por tipo, para servir de base à tabela de símbolos e às verificações de tipo (Etapa 5).
