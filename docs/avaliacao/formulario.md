# Formulário de avaliação por pares

Para montar no Google Forms. Configuração: **não coletar e-mails**, não exigir login, respostas anônimas. Escala Likert de 1 (discordo totalmente) a 5 (concordo totalmente) em todas as partes D, E e F.

## A. Termo de consentimento

> Você está convidado(a) a avaliar um software educacional de compiladores desenvolvido como trabalho da disciplina de Compiladores. A participação é voluntária, leva cerca de 30 minutos e pode ser interrompida a qualquer momento, sem qualquer efeito em notas. Não coletamos nome, e-mail, matrícula ou outros dados de identificação. As respostas serão apresentadas apenas de forma agregada. O código que você digitar nas tarefas será usado somente para analisar as mensagens de erro do software.
>
> ( ) Li e concordo em participar.

## B. Perfil

1. Curso: ( ) Ciência da Computação ( ) Inteligência Artificial ( ) Outro
2. Situação: ( ) Cursando Compiladores ( ) Já cursei Compiladores ( ) Sou professor(a)
3. Familiaridade com a linguagem C (1 = nenhuma, 5 = muita): 1 2 3 4 5
4. Dispositivo usado: ( ) Computador ( ) Celular ( ) Tablet
5. Navegador: ( ) Chrome ( ) Edge ( ) Firefox ( ) Safari ( ) Outro

## C. Tarefas

Registre a resposta e, se possível, o tempo aproximado em minutos.

- **T1.** Analise o exemplo 1. Quantos tokens do tipo identificador foram reconhecidos?
- **T2.** Analise o código `int total = 5 @ 2;`. Em que linha e coluna está o erro léxico e qual é o caractere?
- **T3.** Analise `int resultado = 10 + 5 * 2;`. Qual operador aparece na raiz da expressão na AST? Clique no nó `MULTIPLICACAO`: qual regra gramatical é mostrada?
- **T4.** Carregue o exemplo 12 (erros sintáticos variados) e corrija os erros, um de cada vez, analisando após cada correção, até não haver erros. Após cada correção, copie o código e cole no campo abaixo.
- **T5.** Com o exemplo 9 (precedência), use a construção passo a passo da AST. Qual é o primeiro nó construído e qual é o último?
- **T6.** *(Somente se a análise semântica estiver disponível.)* Em um programa com uma variável usada sem declaração, em que fase o erro é apontado e qual variável é?

## D. Usabilidade (SUS — Brooke, 1996)

1. Eu acho que gostaria de usar este sistema com frequência.
2. Achei o sistema desnecessariamente complexo.
3. Achei o sistema fácil de usar.
4. Acho que precisaria do apoio de uma pessoa técnica para conseguir usar este sistema.
5. Achei que as várias funções do sistema estão bem integradas.
6. Achei que o sistema tem muita inconsistência.
7. Imagino que a maioria das pessoas aprenderia a usar este sistema rapidamente.
8. Achei o sistema muito complicado de usar.
9. Eu me senti confiante ao usar o sistema.
10. Precisei aprender muitas coisas antes de conseguir usar o sistema.

Cálculo: itens ímpares → (resposta − 1); itens pares → (5 − resposta); soma × 2,5 (0 a 100).

## E. Funcionalidades

- **Q1.** A interface foi fácil de entender e de usar.
- **Q2.** Consegui inserir um código-fonte e executar a análise sem ajuda.
- **Q3.** As mensagens de erro foram claras e úteis.
- **Q4.** A visualização dos tokens ajudou a compreender a análise léxica.
- **Q5.** A visualização da AST ajudou a compreender a estrutura do programa.
- **Q6.** A apresentação da análise semântica foi compreensível. *(somente se implementada)*
- **Q7.** As explicações sobre as etapas da compilação foram úteis.
- **Q8.** O tutorial foi suficiente para começar a usar a ferramenta.
- **Q9.** O software contribuiu para minha compreensão sobre compiladores.

## F. Diferencial

- **D1.** Ver as fases léxica e sintática na mesma tela ajudou a entender a relação entre elas.
- **D2.** A separação dos erros por fase (léxico, sintático, semântico) deixou claro em que fase cada problema foi detectado.
- **D3.** Poder recolher e expandir partes da AST facilitou a leitura de programas maiores.
- **D4.** Selecionar um nó da AST e ver o trecho correspondente destacado no código ajudou a relacionar a árvore com o programa.
- **D5.** O formato "esperado × encontrado", com linha e coluna, ajudou a corrigir os erros.
- **D6.** Avançar e voltar na construção passo a passo da AST ajudou a entender como a árvore é construída.
- **D7.** Introduzir erros de propósito e ver como são detectados ajudou a entender o funcionamento do compilador.
- **D8.** Usar a ferramenta no navegador, sem instalar nada além do Docker (ou acessando um endereço), foi simples.
- **D9.** Ver a regra gramatical do nó selecionado e do erro sintático ajudou a relacionar a gramática com o programa.

Somente para professores:

- **P1.** Eu usaria a ferramenta em aula ou em atividades de Compiladores.
- **P2.** Os exemplos prontos são adequados ao nível dos estudantes.

## G. Perguntas abertas

1. Você encontrou algum problema técnico ou de usabilidade? Qual?
2. Alguma mensagem de erro foi confusa? Qual e por quê?
3. O que mais ajudou e o que mais atrapalhou?
4. Quais melhorias você sugere?
5. Se usou celular ou tablet, o que funcionou e o que não funcionou?

## Rubrica para as edições da T4 (critério C7)

Adaptada de Marceau, Fisler e Krishnamurthi (2011). Dois codificadores classificam, de forma independente, a primeira edição após cada erro:

| Código | Significado |
|---|---|
| FIX | Corrige o erro apontado pela mensagem (outros erros podem continuar). |
| PART | Mostra que a mensagem foi entendida e tenta uma ação adequada, mas incompleta. |
| DIFF | Não trata o erro apontado, mas corrige outro problema. |
| UNR | Edição não relacionada que não ajuda. |
| DEL | Apaga o trecho problemático inteiro em vez de corrigi-lo. |

Concordância entre codificadores: kappa de Cohen (meta ≥ 0,8). Meta de eficácia: ≥ 70% FIX + PART. Critérios C12–C16 em `docs/materiais-e-metodos.md`.
