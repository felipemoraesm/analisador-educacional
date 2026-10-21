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
