// Testes de interface da Etapa 3: exibição dos tokens, erros léxicos e passo a passo.
const test = require('node:test');
const assert = require('node:assert/strict');
const { montar, resposta, FIXTURES } = require('./auxiliar');
const Visual = require('../visual.js');

const texto = (no) => no.textContent.replace(/\s+/g, ' ').trim();

async function analisar(fixture) {
  const t = await montar();
  t.digitar(FIXTURES[fixture].codigo);
  await t.clicar();
  return t;
}
const linhasTabela = (t) => [...t.doc.querySelectorAll('#tabela-tokens-corpo tr')]
  .map((tr) => [...tr.children].map((td) => td.textContent));
const botao = (t, id) => t.doc.getElementById(id);
const clicar = (t, id) => botao(t, id).click();
const narracao = (t) => t.doc.getElementById('passos-narracao').textContent;
const info = (t) => t.doc.getElementById('passos-info').textContent;

/* ================= Painéis aparecem apenas após uma análise ================= */
test('antes da análise os painéis léxicos ficam ocultos, e o tutorial existe', async () => {
  const t = await montar();
  assert.equal(t.$('painel-lexico').hidden, true);
  assert.equal(t.$('bloco-lexico').hidden, true);
  assert.ok(t.$('tutorial'));
  assert.equal(t.doc.querySelectorAll('#tutorial svg').length, 2);
});

test('a legenda do tutorial lista as 11 categorias de token', async () => {
  const t = await montar();
  assert.equal(t.doc.querySelectorAll('#legenda-categorias tbody tr').length, 11);
  assert.match(texto(t.$('legenda-categorias')), /Palavra reservada.*Operador de atribuição.*Delimitador/);
});

/* ================= Tabela, resumo, cores, sequência ================= */
test('a tabela mostra tipo, lexema, linha e coluna de cada token', async () => {
  const t = await analisar('valido');
  assert.equal(t.$('painel-lexico').hidden, false);
  assert.deepEqual(linhasTabela(t), [
    ['1', 'PALAVRA_RESERVADA', 'int', '1', '1'],
    ['2', 'IDENTIFICADOR', 'numero', '1', '5'],
    ['3', 'OPERADOR_ATRIBUICAO', '=', '1', '12'],
    ['4', 'LITERAL_INTEIRO', '10', '1', '14'],
    ['5', 'DELIMITADOR', ';', '1', '16'],
  ]);
});

test('o resumo mostra a contagem de tokens e a contagem por categoria', async () => {
  const t = await analisar('valido');
  assert.match(texto(t.$('resumo-lexico')), /5 tokens · 0 erros léxicos · 0 comentários ignorados/);
  const chips = [...t.doc.querySelectorAll('#resumo-lexico .chip')].map(texto);
  assert.deepEqual(chips, [
    'Palavra reservada 1', 'Identificador 1', 'Literal inteiro 1', 'Operador de atribuição 1', 'Delimitador 1',
  ]);
});

test('o código colorido preserva o texto e usa uma cor (classe) por categoria', async () => {
  const t = await analisar('valido');
  const pre = t.$('codigo-colorido');
  assert.equal(pre.textContent, FIXTURES.valido.codigo);
  const classes = [...pre.querySelectorAll('span.tk')].map((s) => s.className.replace('tk ', ''));
  assert.deepEqual(classes, ['tk-reservada', 'tk-identificador', 'tk-atribuicao', 'tk-inteiro', 'tk-delimitador']);
});

test('a sequência de tokens usa o formato <categoria, lexema>', async () => {
  const t = await analisar('valido');
  const itens = [...t.doc.querySelectorAll('#sequencia-tokens .seq-item')].map((e) => e.textContent);
  assert.deepEqual(itens, ['<RESERV, int>', '<ID, numero>', '<ATRIB, =>', '<INT, 10>', '<DELIM, ;>']);
});

test('comentários aparecem em cinza no código, são contados e não entram na tabela', async () => {
  const t = await analisar('completo');
  assert.ok(t.$('codigo-colorido').querySelector('.tk-comentario'));
  assert.match(texto(t.$('resumo-lexico')), /1 comentário ignorado/);
  assert.ok(!linhasTabela(t).some((l) => l[2].includes('comentario')));
  assert.equal(t.$('codigo-colorido').textContent, FIXTURES.completo.codigo);
});

test('mensagem de status da análise sem erros é verde e informa tokens', async () => {
  const t = await analisar('valido');
  assert.ok(t.resultado.classList.contains('resultado--sucesso'));
  assert.match(t.resultado.textContent, /Análise léxica concluída: 5 tokens, nenhum erro léxico\./);
  assert.match(t.$('erros-lexicos').textContent, /Nenhum erro léxico encontrado\./);
});

/* ================= Erros léxicos ================= */
test('erros léxicos: mensagem didática com linha, coluna e dica', async () => {
  const t = await analisar('com_erros');
  const itens = [...t.doc.querySelectorAll('#erros-lexicos .erro-item')].map(texto);
  assert.equal(itens.length, 4);
  assert.equal(
    itens[0],
    "Erro léxico na linha 2, coluna 19: caractere não reconhecido: '@'. Verifique se ele faz parte do subconjunto suportado.",
  );
  assert.match(itens[1], /linha 3, coluna 14: literal real malformado '3\.'.*faltam dígitos/);
  assert.match(itens[2], /linha 4, coluna 10: string não fechada/);
  assert.match(itens[3], /linha 5, coluna 1: comentário de bloco não fechado/);
});

test('com erros léxicos o status é amarelo, mas tokens válidos continuam na tabela', async () => {
  const t = await analisar('com_erros');
  assert.ok(t.resultado.classList.contains('resultado--aviso'));
  assert.match(t.resultado.textContent, /3 erros léxicos|4 erros léxicos/);
  assert.ok(linhasTabela(t).length > 10);
  assert.equal(t.$('painel-lexico').hidden, false);
});

test('erros aparecem sublinhados no código colorido e o texto não muda', async () => {
  const t = await analisar('com_erros');
  const erros = [...t.$('codigo-colorido').querySelectorAll('.tk-erro')];
  assert.equal(erros.length, 4);
  assert.equal(erros[0].textContent, '@');
  assert.match(erros[0].title, /Erro léxico na linha 2, coluna 19/);
  assert.equal(t.$('codigo-colorido').textContent, FIXTURES.com_erros.codigo);
});

test('a interface não quebra com os erros: dá para analisar de novo outro código', async () => {
  const t = await analisar('com_erros');
  t.digitar(FIXTURES.valido.codigo);
  await t.clicar();
  assert.equal(linhasTabela(t).length, 5);
  assert.equal(t.doc.querySelectorAll('#erros-lexicos .erro-item').length, 0);
  assert.equal(t.doc.querySelectorAll('#codigo-colorido .tk-erro').length, 0);
});

test('mensagemErro (unidade)', () => {
  assert.equal(
    Visual.mensagemErro({ linha: 2, coluna: 10, mensagem: "Caractere não reconhecido: '@'", dica: 'Dica.' }),
    "Erro léxico na linha 2, coluna 10: caractere não reconhecido: '@'. Dica.",
  );
  assert.equal(
    Visual.mensagemErro({ linha: 1, coluna: 1, mensagem: 'Já termina com ponto.' }),
    'Erro léxico na linha 1, coluna 1: já termina com ponto.',
  );
});

/* ================= Substituição e limpeza ================= */
test('uma nova análise substitui os resultados anteriores (sem duplicar linhas)', async () => {
  const t = await analisar('valido');
  t.digitar(FIXTURES.completo.codigo);
  await t.clicar();
  const n = FIXTURES.completo.resposta.tokens.length;
  assert.equal(linhasTabela(t).length, n);
  assert.equal(t.doc.querySelectorAll('#sequencia-tokens .seq-item').length, n);
});

test('falha de comunicação, entrada inválida e Limpar escondem os painéis léxicos', async () => {
  let t = await analisar('valido');
  t.digitar('   ');
  await t.clicar();
  assert.equal(t.$('painel-lexico').hidden, true);

  t = await analisar('valido');
  t.limpar.click();
  assert.equal(t.$('painel-lexico').hidden, true);
  assert.equal(t.$('bloco-lexico').hidden, true);

  const falha = await montar({ '/api/analisar': async () => { throw new TypeError('rede'); } });
  falha.digitar('int a;');
  await falha.clicar();
  assert.equal(falha.$('painel-lexico').hidden, true);
  assert.match(falha.resultado.textContent, /Falha de comunicação/);
});

test('o exemplo selecionado pode ser analisado e mostra tokens (código vem do fixture real)', async () => {
  const t = await montar();
  t.digitar(FIXTURES.completo.codigo);
  await t.clicar();
  assert.equal(t.fetch.analises().length, 1);
  assert.equal(JSON.parse(t.fetch.analises()[0].opcoes.body).codigo, FIXTURES.completo.codigo);
});

/* ================= Passo a passo ================= */
test('passo a passo: estado inicial', async () => {
  const t = await analisar('valido');
  assert.match(info(t), /Passo 0 de 16/);
  assert.match(narracao(t), /Pronto para começar/);
  assert.equal(botao(t, 'passo-anterior').disabled, true);
  assert.equal(botao(t, 'passo-proximo').disabled, false);
  assert.equal(t.$('passos-codigo').textContent, FIXTURES.valido.codigo);
});

test('passo a passo: Próximo lê um caractere e mostra o estado do autômato', async () => {
  const t = await analisar('valido');
  clicar(t, 'passo-proximo');
  assert.match(info(t), /Passo 1 de 16/);
  assert.match(narracao(t), /Lendo 'i' \(classe: letra\) → estado IDENT\. Lexema até agora: "i"\./);
  assert.equal(t.doc.querySelector('#passos-codigo .passo-atual').textContent, 'i');
  clicar(t, 'passo-proximo');
  clicar(t, 'passo-proximo');
  assert.equal(t.doc.querySelector('#passos-codigo .passo-atual').textContent, 'int');
  assert.match(narracao(t), /token é emitido: <RESERV, int>.*palavras reservadas/);
  assert.equal(t.doc.querySelectorAll('#passos-transicoes .trans').length, 3);
  assert.match(texto(t.$('passos-emitidos')), /Tokens reconhecidos até aqui: 1/);
});

test('passo a passo: espaços são um passo próprio e dizem que são descartados', async () => {
  const t = await analisar('valido');
  for (let i = 0; i < 4; i++) clicar(t, 'passo-proximo');
  assert.match(narracao(t), /Espaços em branco.*descartados/);
});

test('passo a passo: Próximo token / Token anterior / Início / Fim', async () => {
  const t = await analisar('valido');
  clicar(t, 'passo-token-proximo');
  assert.match(info(t), /Passo 3 de 16/);
  clicar(t, 'passo-token-proximo'); // espaço
  clicar(t, 'passo-token-proximo'); // "numero" inteiro
  assert.equal(t.doc.querySelector('#passos-codigo .passo-atual').textContent, 'numero');
  clicar(t, 'passo-token-anterior');
  assert.match(info(t), /Passo 4 de 16/); // volta ao fim do espaço anterior
  clicar(t, 'passo-fim');
  assert.match(info(t), /Passo 16 de 16/);
  assert.match(narracao(t), /Fim da entrada/);
  assert.equal(botao(t, 'passo-proximo').disabled, true);
  assert.match(texto(t.$('passos-emitidos')), /Tokens reconhecidos até aqui: 5/);
  clicar(t, 'passo-inicio');
  assert.match(info(t), /Passo 0 de 16/);
  assert.equal(botao(t, 'passo-anterior').disabled, true);
});

test('passo a passo: Anterior desfaz o passo (sem estado residual)', async () => {
  const t = await analisar('valido');
  clicar(t, 'passo-proximo'); clicar(t, 'passo-proximo');
  const antes = narracao(t);
  clicar(t, 'passo-proximo');
  clicar(t, 'passo-anterior');
  assert.equal(narracao(t), antes);
});

test('passo a passo: números reais mostram o caminho INT, REAL_PONTO e REAL', async () => {
  const t = await analisar('completo');
  const passos = Visual.construirPassos(FIXTURES.completo.codigo, FIXTURES.completo.resposta);
  const fim = passos.findIndex((p) => p.tipo === 'token' && p.item.lexema === '1.75' && p.final) + 1;
  for (let i = 0; i < fim; i++) clicar(t, 'passo-proximo');
  const estados = [...t.doc.querySelectorAll('#passos-transicoes .trans u')].map((u) => u.textContent);
  assert.deepEqual(estados, ['INT', 'REAL_PONTO', 'REAL', 'REAL']);
  assert.match(narracao(t), /token é emitido: <REAL, 1\.75> \(Literal real\)/);
});

test('passo a passo (com erro): o último estado é ERRO e a narração traz a mensagem', async () => {
  const t = await analisar('com_erros');
  // avança até o erro de '@' (passo final do item de erro)
  const passos = Visual.construirPassos(FIXTURES.com_erros.codigo, FIXTURES.com_erros.resposta);
  const alvo = passos.findIndex((p) => p.tipo === 'erro' && p.item.lexema === '@') + 1;
  for (let i = 0; i < alvo; i++) clicar(t, 'passo-proximo');
  assert.match(narracao(t), /Lendo '@'.*estado ERRO.*Erro léxico na linha 2, coluna 19/);
  assert.ok(t.doc.querySelector('#passos-transicoes .trans--erro'));
});

test('passo a passo: erro sem caminho (comentário não fechado) vira um único passo', async () => {
  const dados = FIXTURES.com_erros.resposta;
  const passos = Visual.construirPassos(FIXTURES.com_erros.codigo, dados);
  const ultimo = passos[passos.length - 1];
  assert.equal(ultimo.tipo, 'erro');
  assert.equal(ultimo.total, 0);
  assert.match(Visual.narrar(ultimo, FIXTURES.com_erros.codigo), /comentário de bloco não fechado/);
});

test('construirPassos: um passo por caractere de token mais um por trecho de espaços', async () => {
  const passos = Visual.construirPassos(FIXTURES.valido.codigo, FIXTURES.valido.resposta);
  assert.equal(passos.length, 13 + 3);
  assert.ok(passos[passos.length - 1].final);
  assert.equal(passos.filter((p) => p.tipo === 'espaco').length, 3);
});

test('construirPassos cobre todo o código em ordem (fimLido nunca decresce e termina no fim)', async () => {
  for (const nome of Object.keys(FIXTURES)) {
    const f = FIXTURES[nome];
    const passos = Visual.construirPassos(f.codigo, f.resposta);
    let anterior = 0;
    for (const p of passos) { assert.ok(p.fimLido >= anterior, nome); anterior = p.fimLido; }
    assert.equal(anterior, f.codigo.length, nome);
  }
});

test('emoji: posições UTF-16 recortam o código corretamente na tela', async () => {
  const t = await analisar('emoji');
  assert.equal(t.$('codigo-colorido').textContent, FIXTURES.emoji.codigo);
  const str = [...t.$('codigo-colorido').querySelectorAll('.tk-string')].map((s) => s.textContent);
  assert.deepEqual(str, ['"😀"']);
  for (let i = 0; i < 40; i++) clicar(t, 'passo-proximo');
  assert.match(info(t), /Passo \d+ de \d+/);
});

/* ================= Reprodução automática (relógio falso) ================= */
function comRelogio(codigo, resposta, montarT) {
  const fila = [];
  const agendar = (fn, ms) => { fila.push({ fn, ms }); return fila.length; };
  const cancelar = (h) => { if (fila[h - 1]) fila[h - 1].cancelado = true; };
  const tick = () => { const f = fila.find((x) => !x.cancelado && !x.feito); if (f) { f.feito = true; f.fn(); return true; } return false; };
  return { agendar, cancelar, tick, fila };
}

test('reproduzir avança um passo por tick até o fim e depois para sozinho', async () => {
  const t = await montar();
  t.doc.getElementById('painel-lexico').hidden = false;
  const r = comRelogio();
  const c = Visual.criarPassoAPasso(t.doc, FIXTURES.valido.codigo, FIXTURES.valido.resposta, { agendar: r.agendar, cancelar: r.cancelar });
  c.reproduzir();
  assert.equal(c.estaTocando(), true);
  assert.equal(botao(t, 'passo-reproduzir').textContent, '⏸ Pausar');
  let ticks = 0;
  while (r.tick()) ticks++;
  assert.equal(c.indice(), c.total());
  assert.equal(c.estaTocando(), false);
  assert.equal(botao(t, 'passo-reproduzir').textContent, '▶ Reproduzir');
  assert.equal(ticks, 16);
  c.destruir();
});

test('pausar interrompe a reprodução; reproduzir retoma do ponto atual', async () => {
  const t = await montar();
  const r = comRelogio();
  const c = Visual.criarPassoAPasso(t.doc, FIXTURES.valido.codigo, FIXTURES.valido.resposta, { agendar: r.agendar, cancelar: r.cancelar });
  c.reproduzir(); r.tick(); r.tick();
  assert.equal(c.indice(), 2);
  c.pausar();
  assert.equal(r.tick(), false); // nada agendado
  assert.equal(c.indice(), 2);
  c.reproduzir(); r.tick();
  assert.equal(c.indice(), 3);
  c.destruir();
});

test('reproduzir no fim reinicia do começo; velocidade muda o intervalo', async () => {
  const t = await montar();
  const r = comRelogio();
  const c = Visual.criarPassoAPasso(t.doc, FIXTURES.valido.codigo, FIXTURES.valido.resposta, { agendar: r.agendar, cancelar: r.cancelar });
  c.irPara(c.total());
  t.doc.getElementById('passo-velocidade').value = 'rapida';
  c.reproduzir();
  assert.equal(c.indice(), 0);
  assert.equal(r.fila[r.fila.length - 1].ms, Visual.VELOCIDADES.rapida);
  c.destruir();
});

test('clicar em outro controle durante a reprodução pausa antes de agir', async () => {
  const t = await montar();
  t.doc.getElementById('painel-lexico').hidden = false;
  const r = comRelogio();
  const c = Visual.criarPassoAPasso(t.doc, FIXTURES.valido.codigo, FIXTURES.valido.resposta, { agendar: r.agendar, cancelar: r.cancelar });
  c.reproduzir();
  clicar(t, 'passo-proximo');
  assert.equal(c.estaTocando(), false);
  assert.equal(c.indice(), 1);
  c.destruir();
});

test('destruir remove os ouvintes (uma nova análise não deixa controles antigos ativos)', async () => {
  const t = await analisar('valido');
  const antigo = t.dom.window.document.getElementById('passo-proximo');
  t.digitar(FIXTURES.completo.codigo);
  await t.clicar();
  clicar(t, 'passo-proximo');
  assert.match(info(t), /Passo 1 de \d+/); // avançou 1, e não 2 (ouvinte antigo removido)
  assert.equal(antigo, botao(t, 'passo-proximo'));
});

test('código sem tokens: passo a passo informa que não há nada a mostrar', async () => {
  const t = await montar();
  t.digitar('   x   ');
  t.entrada.value = '   x   ';
  const dados = { recebido: true, sucesso: true, mensagem: 'm', linhas: 1, caracteres: 7, tokens: [], erros: [], comentarios: [], resumo: { total_tokens: 0, total_erros: 0, total_comentarios: 0, por_categoria: {} } };
  const c = Visual.mostrarAnalise(t.doc, '   ', dados);
  assert.match(narracao(t), /Não há nada para mostrar|Pronto para começar/);
  c.destruir();
});

/* ================= Segurança e robustez ================= */
test('conteúdo vindo do servidor é inserido como texto (sem interpretar HTML)', async () => {
  const t = await montar();
  const malicioso = '<img src=x onerror=alert(1)>';
  const dados = {
    recebido: true, sucesso: false, mensagem: malicioso, linhas: 1, caracteres: 3,
    tokens: [{ tipo: 'IDENTIFICADOR', lexema: malicioso, linha: 1, coluna: 1, inicio: 0, fim: 3, caminho: [{ c: 'a', classe: 'letra', estado: 'IDENT' }, { c: 'b', classe: 'letra', estado: 'IDENT' }, { c: 'c', classe: 'letra', estado: 'IDENT' }] }],
    erros: [{ tipo: 'ERRO_LEXICO', lexema: 'x', linha: 1, coluna: 4, inicio: 3, fim: 4, mensagem: malicioso, dica: malicioso, caminho: [] }],
    comentarios: [], resumo: { total_tokens: 1, total_erros: 1, total_comentarios: 0, por_categoria: { IDENTIFICADOR: 1 } },
  };
  Visual.mostrarAnalise(t.doc, 'abcx', dados);
  assert.equal(t.doc.querySelectorAll('img').length, 0);
  assert.match(t.$('tabela-tokens-corpo').textContent, /<img src=x/);
});

test('dados inconsistentes (intervalos fora do código) não quebram a tela', async () => {
  const t = await montar();
  const dados = {
    recebido: true, sucesso: true, mensagem: 'm', linhas: 1, caracteres: 3,
    tokens: [
      { tipo: 'IDENTIFICADOR', lexema: 'abc', linha: 1, coluna: 1, inicio: 0, fim: 3, caminho: [] },
      { tipo: 'IDENTIFICADOR', lexema: 'zzz', linha: 1, coluna: 1, inicio: 50, fim: 60, caminho: [] },
    ],
    erros: [], comentarios: [], resumo: { total_tokens: 2, total_erros: 0, total_comentarios: 0, por_categoria: { IDENTIFICADOR: 2 } },
  };
  assert.doesNotThrow(() => Visual.mostrarAnalise(t.doc, 'abc', dados));
  assert.equal(t.$('codigo-colorido').textContent, 'abc');
});

test('tabela limita a 2000 linhas e avisa quando há mais tokens', async () => {
  const t = await montar();
  const tokens = Array.from({ length: 2500 }, (_, i) => ({ tipo: 'IDENTIFICADOR', lexema: 'a', linha: 1, coluna: i + 1, inicio: i * 2, fim: i * 2 + 1, caminho: [{ c: 'a', classe: 'letra', estado: 'IDENT' }] }));
  const codigo = 'a '.repeat(2500);
  const dados = { recebido: true, sucesso: true, mensagem: 'm', linhas: 1, caracteres: codigo.length, tokens, erros: [], comentarios: [], resumo: { total_tokens: 2500, total_erros: 0, total_comentarios: 0, por_categoria: { IDENTIFICADOR: 2500 } } };
  const c = Visual.mostrarAnalise(t.doc, codigo, dados);
  assert.equal(t.doc.querySelectorAll('#tabela-tokens-corpo tr').length, 2000);
  assert.match(t.$('tabela-aviso').textContent, /primeiros 2000 de 2500/);
  c.destruir();
});

test('resposta da Etapa 2 (sem tokens) continua funcionando (compatibilidade)', async () => {
  const t = await montar({
    '/api/analisar': () => resposta(200, { recebido: true, mensagem: 'Código recebido com sucesso.', linhas: 1, caracteres: 6 }),
  });
  t.digitar('int a;');
  await t.clicar();
  assert.ok(t.resultado.classList.contains('resultado--sucesso'));
  assert.equal(t.$('painel-lexico').hidden, true);
});
