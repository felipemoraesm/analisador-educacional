"""Exemplos de programas disponibilizados na interface.

Todos usam o subconjunto de C documentado em docs/escopo-lexico.md e docs/gramatica.md.
Os exemplos 1-4, 6, 7, 9, 10 e 11 são válidos (geram AST). O exemplo 5 e o 12 têm erros
sintáticos de propósito (tokens válidos); o exemplo 8 tem erros léxicos (o parser não roda).
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
        "titulo": "5. Erros sintáticos (tokens válidos)",
        "descricao": "Falta ';' e há uma expressão incompleta: o scanner tokeniza normalmente e o parser aponta os dois erros. A variável z não declarada só será detectada na análise semântica (Etapa 5).",
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
    {
        "id": "precedencia",
        "titulo": "9. Precedência e associatividade",
        "descricao": "* antes de +, subtração associa à esquerda, parênteses mudam a árvore, && antes de ||.",
        "codigo": (
            "int resultado = 10 + 5 * 2;\n"
            "int subtracao = 20 - 5 - 3;\n"
            "int parenteses = (10 + 5) * 2;\n"
            "int logica = 1 < 2 && 3 > 4 || !0;\n"
        ),
    },
    {
        "id": "funcoes",
        "titulo": "10. Funções e chamadas",
        "descricao": "Definição de funções com parâmetros, return e chamadas aninhadas.",
        "codigo": (
            "int soma(int a, int b) {\n"
            "    return a + b;\n"
            "}\n"
            "\n"
            "int dobro(int n) {\n"
            "    return soma(n, n);\n"
            "}\n"
            "\n"
            "int resultado = dobro(soma(2, 3));\n"
        ),
    },
    {
        "id": "aninhamento",
        "titulo": "11. while com if/else aninhados",
        "descricao": "Blocos dentro de blocos: a árvore mostra a hierarquia da estrutura.",
        "codigo": (
            "int i = 0;\n"
            "int pares = 0;\n"
            "while (i < 10) {\n"
            "    if (i % 2 == 0) {\n"
            "        pares = pares + 1;\n"
            "    } else {\n"
            "        i = i + 0;\n"
            "    }\n"
            "    i = i + 1;\n"
            "}\n"
        ),
    },
    {
        "id": "erros_sintaticos",
        "titulo": "12. Erros sintáticos variados",
        "descricao": "Expressão incompleta, operadores consecutivos, ')' faltando no if, declaração no corpo do while, parâmetro sem tipo e bloco não fechado.",
        "codigo": (
            "int a = ;\n"
            "int b = 3 + * 4;\n"
            "if (a > 0 {\n"
            "    b = 1;\n"
            "} else {\n"
            "    b = 2;\n"
            "}\n"
            "while (b < 10) int c = 1;\n"
            "int soma(int x, y) { return x; }\n"
            "{ int z = 1;\n"
        ),
    },
]
