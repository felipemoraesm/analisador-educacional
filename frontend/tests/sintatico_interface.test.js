// Testes de interface da Etapa 4: status sintático, erros sintáticos, AST navegável e construção passo a passo.
const test = require('node:test');
const assert = require('node:assert/strict');
const { montar, resposta, FIXTURES } = require('./auxiliar');
const Arvore = require('../arvore.js');

const texto = (no) => no.textContent.replace(/\s+/g, ' ').trim();

async function analisar(fixture, config) {
  const t = await montar(config);
  t.digitar(FIXTURES[fixture].codigo);
  await t.clicar();
  return t;
}
const $ = (t, id) => t.doc.getElementById(id);
const clicar = (t, id) => $(t, id).click();
const li = (t, tipo) => [...t.doc.querySelectorAll(`#ast-arvore li[data-tipo="${tipo}"]`)];
const rotulo = (l) => l.querySelector(':scope > .ast-no__linha .ast-no__rotulo');
const clicarNo = (t, tipo, k = 0) => rotulo(li(t, tipo)[k]).click();
const narr = (t) => $(t, 'ast-narracao').textContent;
const sint = (fixture) => FIXTURES[fixture].resposta.sintatico;

/* ============ Compatibilidade e estado inicial ============ */
test('antes da análise, a seção da AST fica oculta; tutorial e gramática estão na página', async () => {
  const t = await montar();
  assert.equal($(t, 'secao-ast').hidden, true);
  assert.match(texto($(t, 'tutorial')), /Análise sintática e a árvore \(AST\)/);
  assert.match(texto($(t, 'tutorial')), /A gramática \(EBNF\)/);
});

test('a gramática (EBNF) é carregada do backend para o tutorial', async () => {
  const t = await montar();
  assert.match($(t, 'gramatica-ebnf').textContent, /programa = \{ comando \} ;/);
});

test('se a gramática não puder ser carregada, a página avisa e continua funcionando', async () => {
  const t = await montar({ '/api/gramatica': async () => { throw new TypeError('rede'); } });
  assert.match($(t, 'gramatica-ebnf').textContent, /não pôde ser carregada/);
  t.digitar('int a;');
  await t.clicar();
  assert.ok(t.resultado.classList.contains('resultado--sucesso'));
});

test('resposta da Etapa 3 (sem "sintatico") continua funcionando: sem AST e sem quebrar', async () => {
  const f = JSON.parse(JSON.stringify(FIXTURES.valido.resposta));
  delete f.sintatico;
  delete f.lexico;
  const t = await montar({ '/api/analisar': () => resposta(200, f) });
  t.digitar(FIXTURES.valido.codigo);
  await t.clicar();
  assert.equal($(t, 'secao-ast').hidden, true);
  assert.equal(t.$('painel-lexico').hidden, false); // a parte léxica continua
  assert.equal($(t, 'sintatico-status').children.length, 0);
});

/* ============ Sucesso: status e árvore ============ */
test('código válido: status verde e seção da AST visível', async () => {
  const t = await analisar('sintatico_ok');
  assert.equal($(t, 'secao-ast').hidden, false);
  const st = $(t, 'sintatico-status');
  assert.ok(st.classList.contains('resultado--sucesso'));
  assert.match(texto(st), /Análise sintática concluída.*programa válido \(AST com 7 nós\)/);
  assert.equal($(t, 'erros-sintaticos').children.length, 0);
});

test('a árvore reflete a precedência: MULTIPLICACAO está DENTRO de ADICAO', async () => {
  const t = await analisar('sintatico_ok');
  const adicao = li(t, 'ADICAO')[0];
  const mult = li(t, 'MULTIPLICACAO')[0];
  assert.ok(adicao.contains(mult));
  assert.equal(mult.closest('li[data-tipo="ADICAO"]'), adicao);
  assert.equal(li(t, 'LITERAL_INTEIRO').length, 3);
});

test('a árvore usa os papéis ARIA de árvore, com nível e estado de expansão', async () => {
  const t = await analisar('sintatico_ok');
  assert.equal($(t, 'ast-arvore').getAttribute('role'), 'tree');
  const raiz = li(t, 'PROGRAMA')[0];
  assert.equal(raiz.getAttribute('role'), 'treeitem');
  assert.equal(raiz.getAttribute('aria-level'), '1');
  assert.equal(raiz.getAttribute('aria-expanded'), 'true');
  assert.equal(li(t, 'MULTIPLICACAO')[0].getAttribute('aria-level'), '4');
});

test('cada nó mostra papel, tipo, atributos e categoria (com símbolo, sem depender só de cor)', async () => {
  const t = await analisar('sintatico_ok');
  const mult = texto(rotulo(li(t, 'MULTIPLICACAO')[0]));
  assert.match(mult, /direita:/);
  assert.match(mult, /MULTIPLICACAO/);
  assert.match(mult, /\(operador=\*\)/);
  assert.match(mult, /expressão/);
  assert.match(texto(rotulo(li(t, 'PROGRAMA')[0])), /▣.*PROGRAMA.*estrutura/);
  assert.match(texto(rotulo(li(t, 'LITERAL_INTEIRO')[0])), /●.*folha/);
});

test('resumo da árvore: número de nós e altura', async () => {
  const t = await analisar('sintatico_ok');
  assert.match($(t, 'ast-resumo').textContent, /7 nós · altura 5/);
});

test('versão em texto acessível igual à do backend', async () => {
  const t = await analisar('sintatico_ok');
  assert.equal($(t, 'ast-texto').textContent, sint('sintatico_ok').texto);
  assert.match($(t, 'ast-texto').textContent, /ADICAO/);
});

/* ============ Seleção e destaque no código ============ */
test('clicar em um nó destaca o trecho correspondente no código', async () => {
  const t = await analisar('sintatico_ok');
  clicarNo(t, 'MULTIPLICACAO');
  assert.equal($(t, 'ast-codigo').querySelector('.ast-sel').textContent, '5 * 2');
  assert.equal($(t, 'ast-codigo').textContent, FIXTURES.sintatico_ok.codigo);
  clicarNo(t, 'ADICAO');
  assert.equal($(t, 'ast-codigo').querySelector('.ast-sel').textContent, '10 + 5 * 2');
  clicarNo(t, 'PROGRAMA');
  assert.equal($(t, 'ast-codigo').querySelector('.ast-sel').textContent, FIXTURES.sintatico_ok.codigo);
});

test('detalhes do nó: regra gramatical, atributos, posição e tokens do nó', async () => {
  const t = await analisar('sintatico_ok');
  clicarNo(t, 'MULTIPLICACAO');
  const d = texto($(t, 'ast-detalhes'));
  assert.match(d, /Nó: MULTIPLICACAO \(expressão\)/);
  assert.match(d, /Regra gramatical: termo = unario \{ \( "\*" \| "\/" \| "%" \) unario \} ;/);
  assert.match(d, /Atributos: operador=\*/);
  assert.match(d, /Papel no nó pai: direita de ADICAO/);
  assert.match(d, /Posição: linha 1, coluna 22 até linha 1, coluna 27/);
  assert.match(d, /Trecho do código: 5 \* 2/);
  assert.match(d, /Tokens deste nó \(3\)/);
  const chips = [...$(t, 'ast-detalhes').querySelectorAll('.seq-item')].map((c) => c.textContent);
  assert.deepEqual(chips, ['<INT, 5>', '<ARIT, *>', '<INT, 2>']);
});

test('selecionar outro nó troca a seleção (aria-selected e destaque)', async () => {
  const t = await analisar('sintatico_ok');
  clicarNo(t, 'ADICAO');
  clicarNo(t, 'MULTIPLICACAO');
  assert.equal(li(t, 'ADICAO')[0].getAttribute('aria-selected'), 'false');
  assert.equal(li(t, 'MULTIPLICACAO')[0].getAttribute('aria-selected'), 'true');
  assert.equal(t.doc.querySelectorAll('#ast-arvore .ast-no--sel').length, 1);
});

test('sem seleção, o painel de detalhes orienta o usuário', async () => {
  const t = await analisar('sintatico_ok');
  assert.match($(t, 'ast-detalhes').textContent, /Selecione um nó/);
});

/* ============ Expandir, recolher, filtro, exportar ============ */
test('recolher nó: o botão alterna aria-expanded e o texto', async () => {
  const t = await analisar('sintatico_ok');
  const adicao = li(t, 'ADICAO')[0];
  const toggle = adicao.querySelector(':scope > .ast-no__linha .ast-toggle');
  assert.equal(adicao.getAttribute('aria-expanded'), 'true');
  toggle.click();
  assert.equal(adicao.getAttribute('aria-expanded'), 'false');
  assert.equal(toggle.textContent, '▸');
  toggle.click();
  assert.equal(adicao.getAttribute('aria-expanded'), 'true');
});

test('Recolher tudo mantém só a raiz aberta; Expandir tudo reabre', async () => {
  const t = await analisar('sintatico_ok');
  clicar(t, 'ast-recolher');
  assert.equal(li(t, 'PROGRAMA')[0].getAttribute('aria-expanded'), 'true');
  assert.equal(li(t, 'DECLARACAO_VARIAVEL')[0].getAttribute('aria-expanded'), 'false');
  assert.equal(li(t, 'ADICAO')[0].getAttribute('aria-expanded'), 'false');
  clicar(t, 'ast-expandir');
  assert.equal(li(t, 'ADICAO')[0].getAttribute('aria-expanded'), 'true');
  assert.equal(li(t, 'MULTIPLICACAO')[0].getAttribute('aria-expanded'), 'true');
});

test('selecionar um nó em um ramo recolhido o revela', async () => {
  const t = await analisar('sintatico_ok');
  const ctl = t.instancia ? null : null; // (a seleção é feita via clique abaixo)
  clicar(t, 'ast-recolher');
  clicar(t, 'ast-passo-fim'); // nada muda
  clicar(t, 'ast-passo-inicio'); clicar(t, 'ast-passo-proximo'); // seleciona o 1º nó (folha 10), escondido no ramo recolhido
  assert.equal(li(t, 'ADICAO')[0].getAttribute('aria-expanded'), 'true');
  assert.equal($(t, 'ast-codigo').querySelector('.ast-sel').textContent, '10');
});

test('filtro por tipo destaca os nós do tipo e esmaece os demais', async () => {
  const t = await analisar('sintatico_ok');
  const filtro = $(t, 'ast-filtro');
  assert.deepEqual([...filtro.options].map((o) => o.value),
    ['', 'ADICAO', 'DECLARACAO_VARIAVEL', 'LITERAL_INTEIRO', 'MULTIPLICACAO', 'PROGRAMA']);
  filtro.value = 'LITERAL_INTEIRO';
  filtro.dispatchEvent(new t.dom.window.Event('change'));
  assert.equal(t.doc.querySelectorAll('#ast-arvore .ast-no--destaque').length, 3);
  assert.ok(li(t, 'ADICAO')[0].classList.contains('ast-no--filtrado'));
  filtro.value = '';
  filtro.dispatchEvent(new t.dom.window.Event('change'));
  assert.equal(t.doc.querySelectorAll('#ast-arvore .ast-no--destaque, #ast-arvore .ast-no--filtrado').length, 0);
});

test('exportar JSON entrega a AST completa e válida', async () => {
  const t = await montar();
  let recebido = null;
  const f = FIXTURES.sintatico_ok;
  const ctl = Arvore.mostrarSintatico(t.doc, f.codigo, f.resposta, { baixar: (nome, conteudo) => { recebido = { nome, conteudo }; } });
  clicar(t, 'ast-exportar');
  assert.equal(recebido.nome, 'ast.json');
  assert.deepEqual(JSON.parse(recebido.conteudo), f.resposta.sintatico.ast);
  ctl.destruir();
});

/* ============ Construção passo a passo ============ */
test('construção: estado inicial indica árvore completa', async () => {
  const t = await analisar('sintatico_ok');
  assert.match(narr(t), /A árvore está completa/);
  assert.match($(t, 'ast-passo-info').textContent, /Passo 7 de 7/);
  assert.equal($(t, 'ast-passo-proximo').disabled, true);
  assert.equal(t.doc.querySelectorAll('#ast-arvore .ast-no--fantasma').length, 0);
});

test('construção: Início esmaece todos os nós; Próximo os constrói das folhas à raiz', async () => {
  const t = await analisar('sintatico_ok');
  clicar(t, 'ast-passo-inicio');
  assert.match(narr(t), /Nenhum nó foi reconhecido ainda/);
  assert.equal(t.doc.querySelectorAll('#ast-arvore .ast-no--fantasma').length, 7);

  clicar(t, 'ast-passo-proximo'); // 1º: folha 10
  assert.match(narr(t), /Passo 1 de 7: o parser terminou de reconhecer LITERAL_INTEIRO \(valor=10\).*"10".*É uma folha/);
  assert.equal($(t, 'ast-codigo').querySelector('.ast-sel').textContent, '10');
  assert.equal(t.doc.querySelectorAll('#ast-arvore .ast-no--fantasma').length, 6);
  assert.ok(li(t, 'LITERAL_INTEIRO')[0].classList.contains('ast-no--atual'));

  clicar(t, 'ast-passo-proximo'); clicar(t, 'ast-passo-proximo'); // folhas 5 e 2
  clicar(t, 'ast-passo-proximo'); // 4º: MULTIPLICACAO
  assert.match(narr(t), /Passo 4 de 7: .*MULTIPLICACAO \(operador=\*\).*"5 \* 2"/);
  assert.match(narr(t), /combina 2 filhos já prontos: LITERAL_INTEIRO, LITERAL_INTEIRO/);
  assert.match(narr(t), /Regra usada: termo = unario/);
  assert.ok(li(t, 'ADICAO')[0].classList.contains('ast-no--fantasma')); // o pai ainda não foi construído
  assert.ok(!li(t, 'MULTIPLICACAO')[0].classList.contains('ast-no--fantasma'));
});

test('construção: a raiz é o último passo e encerra com mensagem', async () => {
  const t = await analisar('sintatico_ok');
  clicar(t, 'ast-passo-inicio');
  clicar(t, 'ast-passo-fim');
  assert.match($(t, 'ast-passo-info').textContent, /Passo 7 de 7/);
  assert.match(narr(t), /PROGRAMA.*último passo.*árvore está completa/);
  assert.equal(t.doc.querySelectorAll('#ast-arvore .ast-no--fantasma').length, 0);
  assert.equal($(t, 'ast-passo-proximo').disabled, true);
  assert.ok(li(t, 'PROGRAMA')[0].classList.contains('ast-no--atual'));
});

test('construção: Anterior desfaz o passo', async () => {
  const t = await analisar('sintatico_ok');
  clicar(t, 'ast-passo-inicio');
  clicar(t, 'ast-passo-proximo'); clicar(t, 'ast-passo-proximo');
  const antes = narr(t);
  clicar(t, 'ast-passo-proximo');
  clicar(t, 'ast-passo-anterior');
  assert.equal(narr(t), antes);
  assert.equal($(t, 'ast-passo-anterior').disabled, false);
  clicar(t, 'ast-passo-inicio');
  assert.equal($(t, 'ast-passo-anterior').disabled, true);
});

test('construção: a ordem dos passos é pós-ordem (filhos antes dos pais)', async () => {
  const f = FIXTURES.sintatico_funcoes;
  const t = await montar();
  const ctl = Arvore.mostrarSintatico(t.doc, f.codigo, f.resposta);
  const porId = {};
  (function idx(n, pai) { porId[n.id] = { n, pai }; n.filhos.forEach((x) => idx(x, n)); }(f.resposta.sintatico.ast, null));
  const pos = {};
  ctl.ordem.forEach((id, i) => { pos[id] = i; });
  for (const id of ctl.ordem) {
    for (const filho of porId[id].n.filhos) assert.ok(pos[filho.id] < pos[id]);
  }
  assert.equal(ctl.ordem[ctl.ordem.length - 1], 1); // raiz por último
  ctl.destruir();
});

function comRelogio() {
  const fila = [];
  return {
    agendar: (fn, ms) => { fila.push({ fn, ms }); return fila.length; },
    cancelar: (h) => { if (fila[h - 1]) fila[h - 1].cancelado = true; },
    tick: () => { const f = fila.find((x) => !x.cancelado && !x.feito); if (f) { f.feito = true; f.fn(); return true; } return false; },
    fila,
  };
}

test('reproduzir constrói a árvore sozinha até o fim e para', async () => {
  const t = await montar();
  const r = comRelogio();
  const f = FIXTURES.sintatico_ok;
  const ctl = Arvore.mostrarSintatico(t.doc, f.codigo, f.resposta, { agendar: r.agendar, cancelar: r.cancelar });
  ctl.reproduzir(); // como estava completa, recomeça do zero
  assert.equal(ctl.indice(), 0);
  assert.equal(ctl.estaTocando(), true);
  assert.equal($(t, 'ast-passo-reproduzir').textContent, '⏸ Pausar');
  let ticks = 0;
  while (r.tick()) ticks++;
  assert.equal(ticks, 7);
  assert.equal(ctl.indice(), 7);
  assert.equal(ctl.estaTocando(), false);
  assert.equal($(t, 'ast-passo-reproduzir').textContent, '▶ Reproduzir');
  ctl.destruir();
});

test('pausar interrompe; mudar a velocidade reagenda com o novo intervalo', async () => {
  const t = await montar();
  const r = comRelogio();
  const f = FIXTURES.sintatico_ok;
  const ctl = Arvore.mostrarSintatico(t.doc, f.codigo, f.resposta, { agendar: r.agendar, cancelar: r.cancelar });
  ctl.reproduzir(); r.tick(); r.tick();
  assert.equal(ctl.indice(), 2);
  $(t, 'ast-passo-velocidade').value = 'rapida';
  $(t, 'ast-passo-velocidade').dispatchEvent(new t.dom.window.Event('change'));
  assert.equal(r.fila[r.fila.length - 1].ms, Arvore.VELOCIDADES.rapida);
  ctl.pausar();
  assert.equal(r.tick(), false);
  assert.equal(ctl.indice(), 2);
  ctl.destruir();
});

/* ============ Erros sintáticos ============ */
test('erros sintáticos: status amarelo, lista com regra e sem AST', async () => {
  const t = await analisar('sintatico_erro');
  assert.equal($(t, 'secao-ast').hidden, true);
  const st = $(t, 'sintatico-status');
  assert.ok(st.classList.contains('resultado--aviso'));
  assert.match(texto(st), /Erros sintáticos: 2 erros encontrados/);
  assert.match(texto(st), /árvore \(AST\) não foi construída/);
  const itens = [...t.doc.querySelectorAll('#erros-sintaticos .erro-item--sint')].map(texto);
  assert.equal(itens.length, 2);
  assert.match(itens[0], /^Erro sintático na linha 2, coluna 1: era esperado ';' ao final da declaração, mas foi encontrada a palavra reservada 'int'\./);
  assert.match(itens[0], /Esperado: ;/);
  assert.match(itens[0], /Regra da gramática: declaracao = tipo IDENTIFICADOR/);
  assert.match(itens[0], /Confira se faltou ';' no fim da linha anterior/);
  assert.match(itens[1], /linha 2, coluna 13: era esperada uma expressão depois do operador '\+'/);
});

test('erro sintático aparece marcado no código colorido', async () => {
  const t = await analisar('sintatico_erro');
  const marcados = [...t.$('codigo-colorido').querySelectorAll('.tk-sint')].map((s) => s.textContent);
  assert.deepEqual(marcados, ['int', ';']);
  assert.match(t.$('codigo-colorido').querySelector('.tk-sint').title, /Erro sintático aqui/);
  assert.equal(t.$('codigo-colorido').textContent, FIXTURES.sintatico_erro.codigo);
});

test('erro por fim inesperado marca o último token', async () => {
  const f = JSON.parse(JSON.stringify(FIXTURES.sintatico_ok));
  f.codigo = 'int x = 5 + 3';
  f.resposta.sintatico = {
    executado: true, sucesso: false, mensagem: 'm', motivo: null, ast: null, erros_truncados: false, resumo: null, regras: {}, texto: null,
    erros: [{ tipo: 'ERRO_SINTATICO', linha: 1, coluna: 14, inicio: 13, fim: 13, encontrado: 'fim do código', encontrado_tipo: 'FIM',
      esperado: [';'], mensagem: "Era esperado ';' ao final da declaração, mas o código terminou antes disso.", regra: null, dica: null }],
  };
  const t = await montar();
  Visual = require('../visual.js');
  const pre = t.$('codigo-colorido');
  Visual.renderCodigoColorido(t.doc, pre, f.codigo, { ...f.resposta, tokens: f.resposta.tokens.slice(0, 7), erros: [], comentarios: [] });
  assert.ok([...pre.querySelectorAll('span')].pop().classList.contains('tk-sint-fim'));
});

test('erros léxicos: o parser não roda, e o motivo aparece junto dos erros léxicos', async () => {
  const t = await analisar('com_erros');
  assert.equal($(t, 'secao-ast').hidden, true);
  assert.match(texto($(t, 'sintatico-status')), /Análise sintática não executada/);
  assert.match(texto($(t, 'sintatico-status')), /não foi executada porque o código tem erros léxicos/);
  assert.equal(t.doc.querySelectorAll('#erros-sintaticos .erro-item--sint').length, 0);
  assert.equal(t.doc.querySelectorAll('#erros-lexicos .erro-item').length, 4); // os erros léxicos continuam aparecendo
});

test('erro léxico e erro sintático são visualmente distintos', async () => {
  const lex = await analisar('com_erros');
  const sin = await analisar('sintatico_erro');
  const itemLex = lex.doc.querySelector('#erros-lexicos .erro-item');
  const itemSin = sin.doc.querySelector('#erros-sintaticos .erro-item');
  assert.ok(!itemLex.classList.contains('erro-item--sint'));
  assert.ok(itemSin.classList.contains('erro-item--sint'));
  assert.match(itemLex.textContent, /^Erro léxico/);
  assert.match(itemSin.textContent, /^Erro sintático/);
  const titulos = [...sin.doc.querySelectorAll('#bloco-lexico .subtitulo')].map(texto);
  assert.deepEqual(titulos, ['Erros léxicos', 'Análise sintática']);
});

test('aviso quando o limite de erros foi atingido', async () => {
  const dados = JSON.parse(JSON.stringify(FIXTURES.sintatico_erro.resposta));
  dados.sintatico.erros_truncados = true;
  const t = await montar();
  Arvore.mostrarSintatico(t.doc, FIXTURES.sintatico_erro.codigo, dados);
  assert.match(texto($(t, 'erros-sintaticos')), /apenas os primeiros erros/);
});

test('mensagemErroSintatico (unidade) segue o formato do enunciado', () => {
  assert.equal(
    Arvore.mensagemErroSintatico({ linha: 3, coluna: 12, mensagem: "Era esperado ')' para fechar a condição do if, mas foi encontrado '{'." }),
    "Erro sintático na linha 3, coluna 12: era esperado ')' para fechar a condição do if, mas foi encontrado '{'.",
  );
});

/* ============ Substituição, consistência e robustez ============ */
test('nova análise substitui a árvore anterior (sem nós duplicados)', async () => {
  const t = await analisar('sintatico_ok');
  t.digitar(FIXTURES.sintatico_funcoes.codigo);
  await t.clicar();
  const n = FIXTURES.sintatico_funcoes.resposta.sintatico.resumo.total_nos;
  assert.equal(t.doc.querySelectorAll('#ast-arvore li').length, n);
  assert.equal(t.doc.querySelectorAll('#ast-arvore > li').length, 1);
});

test('depois de um código com erro, a árvore anterior some', async () => {
  const t = await analisar('sintatico_ok');
  t.digitar(FIXTURES.sintatico_erro.codigo);
  await t.clicar();
  assert.equal($(t, 'secao-ast').hidden, true);
  t.limpar.click();
  assert.equal($(t, 'sintatico-status').children.length, 0);
});

test('Limpar e falha de comunicação escondem a seção da AST', async () => {
  let t = await analisar('sintatico_ok');
  t.limpar.click();
  assert.equal($(t, 'secao-ast').hidden, true);
  t = await analisar('sintatico_ok');
  t.digitar('   ');
  await t.clicar();
  assert.equal($(t, 'secao-ast').hidden, true);
});

test('consistência: cada folha da AST corresponde a uma linha da tabela de tokens (tipo, lexema, linha e coluna)', async () => {
  const t = await analisar('sintatico_funcoes');
  const linhas = [...t.doc.querySelectorAll('#tabela-tokens-corpo tr')].map((tr) => [...tr.children].map((td) => td.textContent));
  const folhas = [];
  (function rec(n) {
    if (n.tipo === 'IDENTIFICADOR' || n.tipo.startsWith('LITERAL_')) folhas.push(n);
    n.filhos.forEach(rec);
  }(FIXTURES.sintatico_funcoes.resposta.sintatico.ast));
  assert.equal(folhas.length, 4);
  for (const f of folhas) {
    const valor = f.atributos.nome || f.atributos.valor;
    assert.ok(
      linhas.some((l) => l[1] === f.tipo && l[2] === valor && l[3] === String(f.linha) && l[4] === String(f.coluna)),
      `${f.tipo} ${valor} @${f.linha}:${f.coluna}`,
    );
  }
});

test('consistência: o número de tokens do nó raiz é o total da tabela', async () => {
  const t = await analisar('sintatico_funcoes');
  clicarNo(t, 'PROGRAMA');
  const total = FIXTURES.sintatico_funcoes.resposta.resumo.total_tokens;
  assert.match(texto($(t, 'ast-detalhes')), new RegExp(`Tokens deste nó \\(${total}\\)`));
});

test('texto vindo do servidor na árvore é inserido como texto (sem interpretar HTML)', async () => {
  const f = JSON.parse(JSON.stringify(FIXTURES.sintatico_ok));
  const mal = '<img src=x onerror=alert(1)>';
  f.resposta.sintatico.ast.filhos[0].atributos.nome = mal;
  f.resposta.sintatico.regras.PROGRAMA.regra = mal;
  f.resposta.sintatico.texto = mal;
  const t = await montar();
  const ctl = Arvore.mostrarSintatico(t.doc, f.codigo, f.resposta);
  clicarNo(t, 'PROGRAMA');
  assert.equal(t.doc.querySelectorAll('img').length, 0);
  assert.match(texto($(t, 'ast-arvore')), /<img src=x/);
  ctl.destruir();
});

test('árvore grande: nós são criados sob demanda e a interface continua leve', async () => {
  const filhos = Array.from({ length: 5000 }, (_, i) => ({
    tipo: 'LITERAL_INTEIRO', id: i + 2, papel: 'item', linha: 1, coluna: 1, fim_linha: 1, fim_coluna: 2, inicio: 0, fim: 1,
    atributos: { valor: String(i) }, filhos: [],
  }));
  const ast = { tipo: 'PROGRAMA', id: 1, papel: null, linha: 1, coluna: 1, fim_linha: 1, fim_coluna: 2, inicio: 0, fim: 1, atributos: {}, filhos };
  const dados = { tokens: [], sintatico: { executado: true, sucesso: true, mensagem: 'm', motivo: null, erros: [], ast,
    resumo: { total_nos: 5001, altura: 2, por_tipo: { PROGRAMA: 1, LITERAL_INTEIRO: 5000 } }, regras: {}, texto: null } };
  const t = await montar();
  const inicio = Date.now();
  const ctl = Arvore.mostrarSintatico(t.doc, 'x', dados);
  assert.ok(Date.now() - inicio < 2000);
  // raiz expandida até o nível 3: os 5000 filhos diretos são criados, mas nada além disso
  assert.ok(t.doc.querySelectorAll('#ast-arvore li').length <= 5001);
  assert.match($(t, 'ast-resumo').textContent, /5001 nós/);
  assert.match($(t, 'ast-resumo').textContent, /Expandir tudo" abre só os 6 primeiros níveis/);
  assert.match($(t, 'ast-texto').textContent, /grande demais para a versão em texto/);
  ctl.destruir();
});

test('programa vazio (só a raiz) é exibido sem erro', async () => {
  const t = await montar();
  t.digitar('// só comentário\nint x;');
  const ast = { tipo: 'PROGRAMA', id: 1, papel: null, linha: 1, coluna: 1, fim_linha: 1, fim_coluna: 1, inicio: 0, fim: 0, atributos: {}, filhos: [] };
  const dados = { tokens: [], sintatico: { executado: true, sucesso: true, mensagem: 'Análise sintática concluída: programa vazio (AST com 1 nó).',
    motivo: null, erros: [], ast, resumo: { total_nos: 1, altura: 1, por_tipo: { PROGRAMA: 1 } }, regras: {}, texto: 'PROGRAMA  [1:1]' } };
  const ctl = Arvore.mostrarSintatico(t.doc, '', dados);
  assert.equal(t.doc.querySelectorAll('#ast-arvore li').length, 1);
  assert.match($(t, 'ast-passo-info').textContent, /Passo 1 de 1/);
  ctl.destruir();
});

test('destruir remove os ouvintes: controles antigos não agem depois de nova análise', async () => {
  const t = await analisar('sintatico_ok');
  t.digitar(FIXTURES.sintatico_funcoes.codigo);
  await t.clicar();
  clicar(t, 'ast-passo-inicio');
  clicar(t, 'ast-passo-proximo');
  assert.match($(t, 'ast-passo-info').textContent, /Passo 1 de \d+/);
});
