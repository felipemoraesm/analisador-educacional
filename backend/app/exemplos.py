"""Exemplos de programas disponibilizados na interface.

Todos pertencem ao subconjunto de C definido no README: variáveis int,
atribuição, operadores aritméticos e relacionais e if/else. O último exemplo
contém erros intencionais, que serão detectados nas próximas etapas.
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
        "titulo": "5. Código com erros intencionais",
        "descricao": "Falta ';', há uma expressão incompleta e uma variável não declarada. Será útil nas análises futuras.",
        "codigo": "int x = 10\nint y = x + ;\nz = 5;\n",
    },
]
