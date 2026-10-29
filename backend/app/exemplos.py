"""Exemplos de programas disponibilizados na interface.

Todos usam o subconjunto léxico de C documentado em docs/escopo-lexico.md.
O exemplo 5 tem erros sintáticos/semânticos, mas tokens válidos (o scanner o
tokeniza normalmente); o exemplo 8 tem erros léxicos de propósito.
"""

EXEMPLOS = [
    {
        "id": "declaracao",
        "titulo": "1. Declaração e inicialização",
        "descricao": "Declara variáveis int, com e sem valor inicial, e usa atribuição.",
        "codigo": "int numero = 10;\nint outro;\noutro = 20;\n",
    },
    {
        "id": "aritmetica",
        "titulo": "2. Operações aritméticas",
        "descricao": "Usa +, -, *, / e parênteses em uma expressão.",
        "codigo": "int a = 10;\nint b = 5;\nint resultado = (a + b) * 2 - b / 5;\n",
    },
    {
        "id": "condicional",
        "titulo": "3. Estrutura condicional (if)",
        "descricao": "Usa o operador relacional > dentro de um if.",
        "codigo": "int numero = 10;\nif (numero > 0) {\n    numero = numero + 1;\n}\n",
    },
    {
        "id": "if_else",
        "titulo": "4. if/else com comentário",
        "descricao": "Combina if/else, operador == e comentário de linha.",
        "codigo": (
            "// Verifica se o valor é zero\n"
            "int valor = 0;\n"
            "int resposta;\n"
            "if (valor == 0) {\n"
            "    resposta = 1;\n"
            "} else {\n"
            "    resposta = 2;\n"
            "}\n"
        ),
    },
    {
        "id": "erro_intencional",
        "titulo": "5. Erros sintáticos/semânticos (tokens válidos)",
        "descricao": "Falta ';', há uma expressão incompleta e uma variável não declarada. São erros sintáticos e semânticos: os tokens são válidos e o scanner os reconhece normalmente.",
        "codigo": "int x = 10\nint y = x + ;\nz = 5;\n",
    },
    {
        "id": "literais",
        "titulo": "6. Tipos e literais",
        "descricao": "Reconhece int, float, char, inteiro, real, string e caractere (com escape).",
        "codigo": (
            "int idade = 21;\n"
            "float altura = 1.75;\n"
            "char letra = 'A';\n"
            "char quebra = '\\n';\n"
            "char texto = \"Ola, mundo!\\n\";\n"
        ),
    },
    {
        "id": "operadores",
        "titulo": "7. Operadores, delimitadores e while",
        "descricao": "Mostra o maior casamento: <= é um token só, e não < seguido de =.",
        "codigo": (
            "int total = 0;\n"
            "int i = 1;\n"
            "while (i <= 10 && total != 50) {\n"
            "    total = total + i * 2 - i / 1 % 3;\n"
            "    i = i + 1;\n"
            "}\n"
            "if (!(total >= 5 || i < 0)) { return 1; } else { return 0; }\n"
        ),
    },
    {
        "id": "erros_lexicos",
        "titulo": "8. Erros léxicos intencionais",
        "descricao": "Caractere inválido, real malformado, caractere com 2 letras, identificador começando com dígito, '&' sozinho, string e comentário não fechados.",
        "codigo": (
            "int valor = 10;\n"
            "int total = valor @ 2;\n"
            "float taxa = 3.;\n"
            "char letra = 'ab';\n"
            "int 2x = 5;\n"
            "if (valor & total) { total = $valor; }\n"
            "char s = \"sem fechar;\n"
            "/* comentario sem fim\n"
        ),
    },
]
