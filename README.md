# Analisador Educacional de Código

Software educacional para visualizar as fases de análise **léxica, sintática e semântica** de uma linguagem de programação. Este repositório contém a **Etapa 1**: estrutura inicial, aplicação web mínima ("Hello, World!") e ambiente Docker.

## 1. Linguagem escolhida e subconjunto

**Linguagem analisada: C.**

**Por quê:** C tem sintaxe regular e enxuta, tipagem estática e uma gramática bem documentada, o que facilita demonstrar cada fase de um compilador (tokens, árvore sintática e checagem de tipos/escopo) sem exigir recursos complexos como classes ou coleta de lixo.

**Subconjunto inicial (a ser ampliado nas próximas etapas):**

| Categoria | Construções |
|---|---|
| Tipos | `int` |
| Declarações | `int x;` e `int x = 5;` |
| Atribuição | `x = expr;` |
| Operadores aritméticos | `+`, `-`, `*`, `/` e parênteses |
| Operadores relacionais | `<`, `>`, `<=`, `>=`, `==`, `!=` |
| Condicionais | `if (...) { ... } else { ... }` |
| Comentários | `// linha` |

Fora do escopo por enquanto: ponteiros, structs, funções, laços, pré-processador e bibliotecas.

## 2. Arquitetura

```
.
├── backend/            # API em Python (FastAPI)
│   ├── app/main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/           # Interface estática servida por Nginx
│   ├── index.html
│   ├── nginx.conf      # também repassa /api/ para o backend
│   └── Dockerfile
├── config/             # Arquivos de configuração (.env.example)
├── docker-compose.yml
└── README.md
```

- **Frontend:** HTML/JS servido pelo Nginx na porta 8080 do host.
- **Backend:** FastAPI (Python 3.12) respondendo em `/api/hello` e `/api/health`.
- **Comunicação:** o navegador chama `/api/hello` no Nginx, que repassa ao contêiner `backend`.
- Banco de dados: não necessário nesta etapa.

## 3. Pré-requisitos

- Docker **24 ou superior**
- Docker Compose **v2 ou superior** (comando `docker compose`)
- Git

Verifique com:

```bash
docker --version
docker compose version
```

## 4. Como executar

```bash
git clone https://github.com/felipemoraesm/analisador-educacional
cd <nome-do-repositorio>

docker compose up --build
```

Acesse **http://localhost:8080**. A página deve exibir **Hello, World!**.

Para rodar em segundo plano: `docker compose up --build -d`.

Para trocar a porta: `cp config/.env.example .env` e edite `FRONTEND_PORT`.

## 5. Como encerrar

```bash
docker compose down
```

Para remover também as imagens construídas: `docker compose down --rmi local`.

## 6. Validação de instalação limpa

Roteiro para simular uma máquina nova:

```bash
docker compose down --rmi local -v
docker builder prune -af
cd .. && rm -rf <nome-do-repositorio>
git clone https://github.com/<seu-usuario>/<nome-do-repositorio>.git
cd <nome-do-repositorio>
docker compose up --build -d
curl http://localhost:8080/api/hello
```

Saída esperada do `curl`: `{"message":"Hello, World!"}`. Depois, abra http://localhost:8080 e confirme a mensagem na página.

Registro da validação (preencha com seus dados):

- Data: ____/____/2026
- Sistema operacional: ________
- Versão do Docker / Compose: ________
- Resultado: ________

## 7. Problemas comuns

| Sintoma | Solução |
|---|---|
| Porta 8080 em uso | Defina `FRONTEND_PORT` em um `.env` |
| Página mostra "Erro" | Veja `docker compose logs backend` |
| `docker compose` não encontrado | Instale o Compose v2 ou use `docker-compose` |

## 8. Próximas etapas

Analisador léxico, analisador sintático e análise semântica para o subconjunto de C definido acima, com visualização na interface web.
