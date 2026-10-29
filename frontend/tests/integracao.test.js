// Testes de integração: cliente do frontend contra um backend REAL.
// Execução:  API_URL=http://localhost:8000 npm run test:integracao
// (com Docker Compose no ar, use API_URL=http://localhost:8080 para passar pelo Nginx)
const test = require('node:test');
const assert = require('node:assert/strict');
const app = require('../app.js');

const API_URL = process.env.API_URL;
const opcoes = { skip: API_URL ? false : 'defina API_URL para executar os testes de integração' };

test('análise de código válido via HTTP real', opcoes, async () => {
  const c = app.criarCliente(fetch, API_URL);
  const r = await c.analisar('int numero = 10;');
  assert.equal(r.tipo, 'sucesso');
  assert.equal(r.dados.recebido, true);
  assert.equal(r.dados.linhas, 1);
});

test('backend rejeita entrada vazia e só com espaços', opcoes, async () => {
  const c = app.criarCliente(fetch, API_URL);
  const vazio = await c.analisar('');
  assert.equal(vazio.tipo, 'entrada');
  assert.equal(vazio.erro, 'codigo_vazio');
  const espacos = await c.analisar('   \n ');
  assert.equal(espacos.erro, 'codigo_somente_espacos');
});

test('caracteres especiais chegam íntegros ao backend (contagem confere)', opcoes, async () => {
  const c = app.criarCliente(fetch, API_URL);
  const codigo = 'x = "ação ✓ 😀"; // <tag> \\n';
  const r = await c.analisar(codigo);
  assert.equal(r.tipo, 'sucesso');
  assert.equal(r.dados.caracteres, [...codigo].length);
});

test('exemplos reais: pelo menos três, e todos são aceitos pela análise', opcoes, async () => {
  const c = app.criarCliente(fetch, API_URL);
  const ex = await c.listarExemplos();
  assert.equal(ex.tipo, 'sucesso');
  assert.ok(ex.exemplos.length >= 3);
  for (const e of ex.exemplos) {
    const r = await c.analisar(e.codigo);
    assert.equal(r.tipo, 'sucesso', e.id);
  }
});

test('endpoint da Etapa 1 continua respondendo (regressão)', opcoes, async () => {
  const r = await fetch(API_URL + '/api/hello');
  assert.equal(r.status, 200);
  assert.deepEqual(await r.json(), { message: 'Hello, World!' });
});

test('servidor inacessível é classificado como falha de comunicação', async () => {
  const c = app.criarCliente(fetch, 'http://127.0.0.1:1'); // porta fechada
  const r = await c.analisar('int a;');
  assert.equal(r.tipo, 'comunicacao');
  assert.match(r.mensagem, /Não foi possível comunicar com o servidor/);
});

// ---------- Etapa 3: análise léxica via HTTP real ----------
test('scanner real: tokens do exemplo da especificação', opcoes, async () => {
  const c = app.criarCliente(fetch, API_URL);
  const r = await c.analisar('int numero = 10;');
  assert.equal(r.tipo, 'sucesso');
  assert.equal(r.dados.sucesso, true);
  assert.deepEqual(
    r.dados.tokens.map((t) => [t.tipo, t.lexema, t.linha, t.coluna]),
    [
      ['PALAVRA_RESERVADA', 'int', 1, 1],
      ['IDENTIFICADOR', 'numero', 1, 5],
      ['OPERADOR_ATRIBUICAO', '=', 1, 12],
      ['LITERAL_INTEIRO', '10', 1, 14],
      ['DELIMITADOR', ';', 1, 16],
    ],
  );
  assert.deepEqual(r.dados.erros, []);
});

test('scanner real: erro léxico retorna sucesso=false com localização, sem derrubar a análise', opcoes, async () => {
  const c = app.criarCliente(fetch, API_URL);
  const r = await c.analisar('int a = 1;\nint b = a @ 2;');
  assert.equal(r.tipo, 'sucesso'); // HTTP 200: a análise foi feita
  assert.equal(r.dados.sucesso, false);
  assert.equal(r.dados.erros.length, 1);
  assert.deepEqual([r.dados.erros[0].lexema, r.dados.erros[0].linha, r.dados.erros[0].coluna], ['@', 2, 11]);
  assert.ok(r.dados.tokens.length > 8); // continuou tokenizando depois do erro
});

test('scanner real: exemplos léxicos da interface', opcoes, async () => {
  const c = app.criarCliente(fetch, API_URL);
  const { exemplos } = await c.listarExemplos();
  const porId = Object.fromEntries(exemplos.map((e) => [e.id, e.codigo]));
  assert.equal((await c.analisar(porId.operadores)).dados.sucesso, true);
  const ruim = await c.analisar(porId.erros_lexicos);
  assert.equal(ruim.dados.sucesso, false);
  assert.equal(ruim.dados.erros.length, 8);
});

test('scanner real: posições em UTF-16 recortam o código igual ao JavaScript', opcoes, async () => {
  const c = app.criarCliente(fetch, API_URL);
  const codigo = 's = "😀😀"; x // ✓ fim\n@';
  const r = await c.analisar(codigo);
  for (const item of [...r.dados.tokens, ...r.dados.erros, ...r.dados.comentarios]) {
    assert.equal(codigo.slice(item.inicio, item.fim), item.lexema);
  }
});
