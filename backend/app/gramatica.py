"""Gramática do subconjunto de C (Etapa 4) e metadados dos nós da AST.

Este módulo é a fonte única da gramática mostrada ao usuário: o texto EBNF
abaixo é servido por ``GET /api/gramatica``, e o teste
``tests/test_gramatica.py`` garante que ``docs/gramatica.md`` está igual a ele.
Os terminais em MAIÚSCULAS são categorias de token do scanner (Etapa 3); os
terminais entre aspas são lexemas fixos.
"""

EBNF = '''\
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
'''

SIMBOLO_INICIAL = "programa"

# Do menor para o maior nível de precedência (todos associativos à esquerda,
# exceto os operadores unários, que são associativos à direita).
PRECEDENCIA = [
    {"nivel": 1, "operadores": ["||"], "associatividade": "esquerda", "descricao": "OU lógico (menor precedência)"},
    {"nivel": 2, "operadores": ["&&"], "associatividade": "esquerda", "descricao": "E lógico"},
    {"nivel": 3, "operadores": ["==", "!="], "associatividade": "esquerda", "descricao": "igualdade"},
    {"nivel": 4, "operadores": ["<", ">", "<=", ">="], "associatividade": "esquerda", "descricao": "relacionais"},
    {"nivel": 5, "operadores": ["+", "-"], "associatividade": "esquerda", "descricao": "adição e subtração"},
    {"nivel": 6, "operadores": ["*", "/", "%"], "associatividade": "esquerda", "descricao": "multiplicação, divisão e resto"},
    {"nivel": 7, "operadores": ["!", "-"], "associatividade": "direita", "descricao": "operadores unários (maior precedência)"},
]

# Terminais da gramática e a categoria de token do scanner que os produz.
TERMINAIS = {
    "IDENTIFICADOR": "IDENTIFICADOR",
    "LITERAL_INTEIRO": "LITERAL_INTEIRO",
    "LITERAL_REAL": "LITERAL_REAL",
    "LITERAL_STRING": "LITERAL_STRING",
    "LITERAL_CHAR": "LITERAL_CHAR",
    '"int" "float" "char" "void" "if" "else" "while" "return"': "PALAVRA_RESERVADA",
    '"+" "-" "*" "/" "%"': "OPERADOR_ARITMETICO",
    '"==" "!=" "<" ">" "<=" ">="': "OPERADOR_RELACIONAL",
    '"&&" "||" "!"': "OPERADOR_LOGICO",
    '"="': "OPERADOR_ATRIBUICAO",
    '"(" ")" "{" "}" ";" ","': "DELIMITADOR",
}

CATEGORIAS_NO = {
    "estrutura": "Estrutura do programa",
    "declaracao": "Declaração e atribuição",
    "controle": "Controle de fluxo",
    "expressao": "Expressão",
    "folha": "Folha (valor ou nome)",
}

_R_PRIM = 'primario = IDENTIFICADOR | chamada | LITERAL_INTEIRO | LITERAL_REAL | LITERAL_STRING | LITERAL_CHAR | "(" expressao ")" ;'

# tipo do nó -> (regra, descrição, categoria)
NOS = {
    "PROGRAMA": ('programa = { definicao_funcao | declaracao | comando } ;',
                 "Raiz da árvore: a sequência de itens do programa.", "estrutura"),
    "DEFINICAO_FUNCAO": ('definicao_funcao = tipo_retorno IDENTIFICADOR "(" [ parametros ] ")" bloco ;',
                         "Definição de função: tipo de retorno, nome, parâmetros e corpo.", "estrutura"),
    "PARAMETRO": ('parametro = tipo IDENTIFICADOR ;', "Parâmetro de uma função: tipo e nome.", "estrutura"),
    "BLOCO": ('bloco = "{" { declaracao | comando } "}" ;', "Grupo de instruções entre chaves.", "estrutura"),
    "DECLARACAO_VARIAVEL": ('declaracao = tipo IDENTIFICADOR [ "=" expressao ] ";" ;',
                            "Declaração de variável, com valor inicial opcional.", "declaracao"),
    "ATRIBUICAO": ('atribuicao = IDENTIFICADOR "=" expressao ";" ;',
                   "Guarda o valor de uma expressão em uma variável.", "declaracao"),
    "CONDICIONAL": ('condicional = "if" "(" expressao ")" comando [ "else" comando ] ;',
                    "if com condição, parte 'então' e parte 'senão' opcional.", "controle"),
    "REPETICAO": ('repeticao = "while" "(" expressao ")" comando ;',
                  "Repete o corpo enquanto a condição for verdadeira.", "controle"),
    "RETORNO": ('retorno = "return" [ expressao ] ";" ;', "Devolve um valor (opcional) e encerra a função.", "controle"),
    "CHAMADA_FUNCAO": ('chamada = IDENTIFICADOR "(" [ argumentos ] ")" ;',
                       "Chamada de função com argumentos.", "expressao"),
    "OPERACAO_LOGICA": ('ou = e { "||" e } ;   e = igualdade { "&&" igualdade } ;',
                        "Operação lógica E (&&) ou OU (||).", "expressao"),
    "COMPARACAO": ('igualdade = relacional { ( "==" | "!=" ) relacional } ;   '
                   'relacional = soma { ( "<" | ">" | "<=" | ">=" ) soma } ;',
                   "Comparação entre dois valores.", "expressao"),
    "ADICAO": ('soma = termo { ( "+" | "-" ) termo } ;', "Soma de dois operandos.", "expressao"),
    "SUBTRACAO": ('soma = termo { ( "+" | "-" ) termo } ;', "Subtração de dois operandos.", "expressao"),
    "MULTIPLICACAO": ('termo = unario { ( "*" | "/" | "%" ) unario } ;',
                      "Multiplicação (precedência maior que soma e subtração).", "expressao"),
    "DIVISAO": ('termo = unario { ( "*" | "/" | "%" ) unario } ;', "Divisão de dois operandos.", "expressao"),
    "MODULO": ('termo = unario { ( "*" | "/" | "%" ) unario } ;', "Resto da divisão.", "expressao"),
    "NEGACAO_LOGICA": ('unario = ( "!" | "-" ) unario | primario ;', "Inverte um valor lógico (!).", "expressao"),
    "MENOS_UNARIO": ('unario = ( "!" | "-" ) unario | primario ;', "Troca o sinal de um valor (-x).", "expressao"),
    "IDENTIFICADOR": (_R_PRIM, "Nome de uma variável.", "folha"),
    "LITERAL_INTEIRO": (_R_PRIM, "Número inteiro.", "folha"),
    "LITERAL_REAL": (_R_PRIM, "Número real.", "folha"),
    "LITERAL_STRING": (_R_PRIM, "Texto entre aspas duplas.", "folha"),
    "LITERAL_CHAR": (_R_PRIM, "Um caractere entre apóstrofos.", "folha"),
}


def regras_dos_tipos(tipos):
    """Metadados (regra, descrição, categoria) apenas dos tipos de nó pedidos."""
    return {
        t: {"regra": NOS[t][0], "descricao": NOS[t][1], "categoria": NOS[t][2]}
        for t in sorted(tipos) if t in NOS
    }


def gramatica_completa():
    """Conteúdo do endpoint GET /api/gramatica."""
    return {
        "simbolo_inicial": SIMBOLO_INICIAL,
        "ebnf": EBNF,
        "precedencia": PRECEDENCIA,
        "terminais": TERMINAIS,
        "categorias_no": CATEGORIAS_NO,
        "nos": {t: {"regra": r, "descricao": d, "categoria": c} for t, (r, d, c) in NOS.items()},
    }
