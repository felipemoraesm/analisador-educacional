// Utilitários compartilhados pelos testes do frontend.
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');
const app = require('../app.js');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

// Respostas REAIS do backend (geradas por scripts/gerar_fixtures.py e conferidas por backend/tests/test_fixtures.py)
const FIXTURES = {};
const PASTA_FIXTURES = path.join(__dirname, 'fixtures');
for (const arquivo of fs.readdirSync(PASTA_FIXTURES)) {
  if (arquivo.endsWith('.json')) {
    FIXTURES[arquivo.replace('.json', '')] = JSON.parse(fs.readFileSync(path.join(PASTA_FIXTURES, arquivo), 'utf8'));
  }
}
const respostaPorCodigo = (codigo) => Object.values(FIXTURES).find((f) => f.codigo === codigo);

const EXEMPLOS = [
  { id: 'e1', titulo: '1. Primeiro', descricao: 'Desc 1', codigo: 'int a = 1;\n' },
  { id: 'e2', titulo: '2. Segundo', descricao: 'Desc 2', codigo: 'int b = 2 + 3;\n' },
  { id: 'e3', titulo: '3. Terceiro', descricao: 'Desc 3', codigo: 'if (a > 0) { a = a + 1; }\n' },
];

function resposta(status, corpo) {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: async () => {
      if (corpo === undefined) throw new Error('sem corpo JSON');
      return corpo;
    },
  };
}

// fetch falso: registra chamadas e permite configurar o comportamento por rota.
function criarFetch(config = {}) {
  const chamadas = [];
  const padrao = {
    '/api/exemplos': () => resposta(200, { exemplos: EXEMPLOS }),
    '/api/gramatica': () => resposta(200, { ebnf: 'programa = { comando } ;\n' }),
    '/api/analisar': (opcoes) => {
      const codigo = JSON.parse(opcoes.body).codigo;
      const real = respostaPorCodigo(codigo);
      if (real) return resposta(200, real.resposta);
      return resposta(200, {
        recebido: true,
        sucesso: true,
        mensagem: 'Análise léxica concluída: 0 tokens, nenhum erro léxico.',
        linhas: codigo.split('\n').length,
        caracteres: codigo.length,
        tokens: [],
        erros: [],
        comentarios: [],
        resumo: { total_tokens: 0, total_erros: 0, total_comentarios: 0, por_categoria: {} },
      });
    },
  };
  const rotas = { ...padrao, ...config };
  const f = async (url, opcoes = {}) => {
    chamadas.push({ url, opcoes });
    const tratador = rotas[url];
    if (!tratador) throw new Error('rota não configurada: ' + url);
    return tratador(opcoes);
  };
  f.chamadas = chamadas;
  f.analises = () => chamadas.filter((c) => c.url === '/api/analisar');
  return f;
}

async function montar(config) {
  const dom = new JSDOM(HTML);
  const doc = dom.window.document;
  const fetch = criarFetch(config);
  const instancia = app.iniciar(doc, fetch);
  await instancia.pronto;
  const $ = (id) => doc.getElementById(id);
  return {
    dom, doc, fetch, $,
    entrada: $('entrada-codigo'),
    botao: $('btn-analisar'),
    limpar: $('btn-limpar'),
    seletor: $('seletor-exemplos'),
    resultado: $('resultado'),
    contador: $('contador'),
    descricao: $('descricao-exemplo'),
    digitar(texto) {
      this.entrada.value = texto;
      this.entrada.dispatchEvent(new dom.window.Event('input', { bubbles: true }));
    },
    escolher(id) {
      this.seletor.value = id;
      this.seletor.dispatchEvent(new dom.window.Event('change', { bubbles: true }));
    },
    async clicar() {
      this.botao.click();
      await new Promise((r) => setImmediate(r));
      await new Promise((r) => setImmediate(r));
    },
  };
}

module.exports = { app, montar, criarFetch, resposta, EXEMPLOS, HTML, FIXTURES };
