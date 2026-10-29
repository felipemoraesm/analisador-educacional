const test = require('node:test');
const assert = require('node:assert/strict');
const { app, montar, resposta, EXEMPLOS } = require('./auxiliar');

/* ======================= Estrutura da tela ======================= */
test('a tela identifica o sistema e a linguagem analisada', async () => {
  const t = await montar();
  assert.match(t.$('titulo-sistema').textContent, /Analisador Educacional/);
  assert.equal(t.$('linguagem-analisada').textContent, 'C');
});

test('a tela contém entrada, botão, resultados e seletor de exemplos', async () => {
  const t = await montar();
  assert.equal(t.entrada.tagName, 'TEXTAREA');
  assert.ok(t.entrada.classList.contains('codigo'));
  assert.equal(t.entrada.getAttribute('spellcheck'), 'false');
  assert.equal(t.botao.textContent.trim(), 'Analisar código');
  assert.equal(t.resultado.getAttribute('role'), 'status');
  assert.equal(t.seletor.tagName, 'SELECT');
});

test('o campo de entrada e o seletor possuem rótulos associados', async () => {
  const t = await montar();
  assert.ok(t.doc.querySelector('label[for="entrada-codigo"]'));
  assert.ok(t.doc.querySelector('label[for="seletor-exemplos"]'));
});

test('o seletor lista os exemplos vindos do backend (mínimo de três)', async () => {
  const t = await montar();
  const opcoes = [...t.seletor.options].filter((o) => o.value);
  assert.equal(opcoes.length, EXEMPLOS.length);
  assert.ok(opcoes.length >= 3);
});

/* ======================= Entrada e edição ======================= */
test('o usuário pode substituir o código inicial e editar o conteúdo', async () => {
  const t = await montar();
  assert.ok(t.entrada.value.length > 0, 'há um código inicial');
  t.digitar('int x = 7;');
  assert.equal(t.entrada.value, 'int x = 7;');
  t.digitar(t.entrada.value + '\nint y = 8;');
  assert.equal(t.entrada.value, 'int x = 7;\nint y = 8;');
});

test('o código digitado permanece após análise bem-sucedida', async () => {
  const t = await montar();
  t.digitar('int x = 7;\n');
  await t.clicar();
  assert.equal(t.entrada.value, 'int x = 7;\n');
});

test('o código digitado permanece após erro de comunicação', async () => {
  const t = await montar({ '/api/analisar': async () => { throw new TypeError('rede'); } });
  t.digitar('int x = 7;');
  await t.clicar();
  assert.equal(t.entrada.value, 'int x = 7;');
});

test('o código é enviado ao backend como JSON, exatamente como digitado', async () => {
  const t = await montar();
  t.digitar('int numero = 10;');
  await t.clicar();
  const [chamada] = t.fetch.analises();
  assert.equal(chamada.opcoes.method, 'POST');
  assert.equal(chamada.opcoes.headers['Content-Type'], 'application/json');
  assert.deepEqual(JSON.parse(chamada.opcoes.body), { codigo: 'int numero = 10;' });
});

test('caracteres especiais, aspas, acentos e emoji são enviados sem alteração', async () => {
  const t = await montar();
  const codigo = 'printf("%d\\n", x); // ação ✓ é 😀 <b>&amp;</b> \t fim';
  t.digitar(codigo);
  await t.clicar();
  assert.equal(JSON.parse(t.fetch.analises()[0].opcoes.body).codigo, codigo);
});

test('código com erros intencionais é enviado normalmente (não se presume validade)', async () => {
  const t = await montar();
  t.digitar('int x = 10\nint y = x + ;');
  await t.clicar();
  assert.equal(t.fetch.analises().length, 1);
  assert.ok(t.resultado.classList.contains('resultado--sucesso'));
});

test('o contador acompanha linhas e caracteres', async () => {
  const t = await montar();
  t.digitar('');
  assert.match(t.contador.textContent, /0 linhas · 0 caracteres/);
  t.digitar('int a;');
  assert.match(t.contador.textContent, /1 linha · 6 caracteres/);
  t.digitar('int a;\nint b;\n');
  assert.match(t.contador.textContent, /2 linhas · 14 caracteres/);
});

/* ======================= Validações no frontend ======================= */
test('entrada vazia: mostra a mensagem e não chama o backend', async () => {
  const t = await montar();
  t.digitar('');
  await t.clicar();
  assert.equal(t.fetch.analises().length, 0);
  assert.ok(t.resultado.classList.contains('resultado--aviso'));
  assert.match(t.resultado.textContent, /Informe um código-fonte antes de solicitar a análise\./);
});

test('entrada só com espaços/quebras/tabs: orienta o usuário e não chama o backend', async () => {
  for (const texto of [' ', '    ', '\n\n', '\t \n']) {
    const t = await montar();
    t.digitar(texto);
    await t.clicar();
    assert.equal(t.fetch.analises().length, 0, JSON.stringify(texto));
    assert.match(t.resultado.textContent, /apenas espaços em branco/);
  }
});

test('validarEntrada (unidade)', () => {
  assert.equal(app.validarEntrada('int a;').ok, true);
  assert.equal(app.validarEntrada('').erro, 'codigo_vazio');
  assert.equal(app.validarEntrada('  \n').erro, 'codigo_somente_espacos');
  assert.equal(app.validarEntrada(undefined).erro, 'codigo_vazio');
  assert.equal(app.validarEntrada(null).ok, false);
});

test('contar (unidade)', () => {
  assert.deepEqual(app.contar(''), { linhas: 0, caracteres: 0 });
  assert.deepEqual(app.contar('a'), { linhas: 1, caracteres: 1 });
  assert.deepEqual(app.contar('a\r\nb\r\n'), { linhas: 2, caracteres: 6 });
});

/* ======================= Exemplos ======================= */
test('cada exemplo é carregado corretamente na área de entrada', async () => {
  for (const ex of EXEMPLOS) {
    const t = await montar();
    t.escolher(ex.id);
    assert.equal(t.entrada.value, ex.codigo, ex.id);
    assert.equal(t.descricao.textContent, ex.descricao);
  }
});

test('escolher outro exemplo substitui o conteúdo anterior', async () => {
  const t = await montar();
  t.escolher('e1');
  assert.equal(t.entrada.value, EXEMPLOS[0].codigo);
  t.escolher('e2');
  assert.equal(t.entrada.value, EXEMPLOS[1].codigo);
  assert.ok(!t.entrada.value.includes(EXEMPLOS[0].codigo));
});

test('o exemplo carregado pode ser editado e depois enviado já modificado', async () => {
  const t = await montar();
  t.escolher('e2');
  t.digitar(t.entrada.value + 'int c = 9;\n');
  await t.clicar();
  const enviado = JSON.parse(t.fetch.analises()[0].opcoes.body).codigo;
  assert.equal(enviado, EXEMPLOS[1].codigo + 'int c = 9;\n');
});

test('selecionar um exemplo não dispara análise nem altera o resultado anterior', async () => {
  const t = await montar();
  t.escolher('e1');
  assert.equal(t.fetch.analises().length, 0);
  assert.ok(t.resultado.classList.contains('resultado--vazio'));
});

test('exemplo selecionado pode ser analisado normalmente', async () => {
  const t = await montar();
  t.escolher('e3');
  await t.clicar();
  assert.ok(t.resultado.classList.contains('resultado--sucesso'));
  assert.equal(JSON.parse(t.fetch.analises()[0].opcoes.body).codigo, EXEMPLOS[2].codigo);
});

test('escolher a opção vazia do seletor não apaga o código', async () => {
  const t = await montar();
  t.digitar('int meu = 1;');
  t.escolher('');
  assert.equal(t.entrada.value, 'int meu = 1;');
});

test('falha ao carregar exemplos: avisa e mantém o editor utilizável', async () => {
  const t = await montar({ '/api/exemplos': async () => { throw new TypeError('rede'); } });
  assert.match(t.resultado.textContent, /Não foi possível carregar os exemplos/);
  t.digitar('int a = 1;');
  await t.clicar();
  assert.ok(t.resultado.classList.contains('resultado--sucesso'));
});

test('resposta malformada de exemplos é tratada sem quebrar a interface', async () => {
  const t = await montar({ '/api/exemplos': () => resposta(200, { outro: 1 }) });
  assert.match(t.resultado.textContent, /Não foi possível carregar os exemplos/);
});

/* ======================= Resultado e comunicação ======================= */
test('sucesso: mostra mensagem do servidor, contagem e aviso de etapas futuras', async () => {
  const t = await montar();
  t.digitar('int a;\nint b;');
  await t.clicar();
  assert.ok(t.resultado.classList.contains('resultado--sucesso'));
  // Etapa 3: a mensagem do servidor passou a descrever a análise léxica (antes: "Código recebido com sucesso.")
  assert.match(t.resultado.textContent, /Análise léxica concluída/);
  assert.match(t.resultado.textContent, /2 linhas · 13 caracteres/);
  assert.match(t.resultado.textContent, /sintática e semântica serão adicionadas nas próximas etapas/);
});

test('erro de validação devolvido pelo backend (400) é exibido como entrada inválida', async () => {
  const t = await montar({
    '/api/analisar': () => resposta(400, { recebido: false, erro: 'codigo_vazio', mensagem: 'Mensagem do servidor.' }),
  });
  t.digitar('int a;');
  await t.clicar();
  assert.ok(t.resultado.classList.contains('resultado--aviso'));
  assert.match(t.resultado.textContent, /Entrada inválida/);
  assert.match(t.resultado.textContent, /Mensagem do servidor\./);
});

test('limite de tamanho (413) é exibido como entrada inválida', async () => {
  const t = await montar({
    '/api/analisar': () => resposta(413, { recebido: false, erro: 'codigo_muito_grande', mensagem: 'Muito grande.' }),
  });
  t.digitar('int a;');
  await t.clicar();
  assert.ok(t.resultado.classList.contains('resultado--aviso'));
});

test('falha de comunicação: mensagem compreensível e interface consistente', async () => {
  const t = await montar({ '/api/analisar': async () => { throw new TypeError('Failed to fetch'); } });
  t.digitar('int a;');
  await t.clicar();
  assert.ok(t.resultado.classList.contains('resultado--erro'));
  assert.match(t.resultado.textContent, /Falha de comunicação/);
  assert.match(t.resultado.textContent, /Não foi possível comunicar com o servidor\. Verifique a conexão e tente novamente\./);
  assert.equal(t.botao.disabled, false);
  assert.equal(t.botao.textContent, 'Analisar código');
});

test('502/503/504 (proxy sem backend) contam como falha de comunicação', async () => {
  for (const status of [502, 503, 504]) {
    const t = await montar({ '/api/analisar': () => resposta(status, undefined) });
    t.digitar('int a;');
    await t.clicar();
    assert.match(t.resultado.textContent, /Falha de comunicação/, String(status));
  }
});

test('erro 500: mensagem genérica, sem vazar detalhes internos', async () => {
  const t = await montar({
    '/api/analisar': () => resposta(500, { erro: 'erro_interno', mensagem: 'Traceback em /app/main.py linha 42' }),
  });
  t.digitar('int a;');
  await t.clicar();
  assert.match(t.resultado.textContent, /Erro inesperado/);
  assert.match(t.resultado.textContent, /Ocorreu um erro inesperado/);
  assert.doesNotMatch(t.resultado.textContent, /Traceback|\/app\//);
});

test('resposta que não é JSON é tratada como erro inesperado', async () => {
  const t = await montar({ '/api/analisar': () => resposta(200, undefined) });
  t.digitar('int a;');
  await t.clicar();
  assert.match(t.resultado.textContent, /Erro inesperado/);
});

test('o botão fica desabilitado durante a requisição e é reabilitado ao final', async () => {
  let liberar;
  const pendente = new Promise((r) => { liberar = r; });
  const t = await montar({
    '/api/analisar': async () => { await pendente; return resposta(200, { recebido: true, mensagem: 'ok', linhas: 1, caracteres: 6 }); },
  });
  t.digitar('int a;');
  t.botao.click();
  await new Promise((r) => setImmediate(r));
  assert.equal(t.botao.disabled, true);
  assert.equal(t.botao.textContent, 'Analisando…');
  liberar();
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  assert.equal(t.botao.disabled, false);
});

test('cliques repetidos durante a requisição não geram envios duplicados', async () => {
  let liberar;
  const pendente = new Promise((r) => { liberar = r; });
  const t = await montar({
    '/api/analisar': async () => { await pendente; return resposta(200, { recebido: true, mensagem: 'ok', linhas: 1, caracteres: 6 }); },
  });
  t.digitar('int a;');
  t.botao.click();
  await new Promise((r) => setImmediate(r));
  t.botao.click();
  t.botao.click();
  liberar();
  await new Promise((r) => setImmediate(r));
  assert.equal(t.fetch.analises().length, 1);
});

test('regressão: após uma falha, uma nova análise válida funciona', async () => {
  let falhar = true;
  const t = await montar({
    '/api/analisar': async (op) => {
      if (falhar) throw new TypeError('rede');
      const c = JSON.parse(op.body).codigo;
      return resposta(200, { recebido: true, mensagem: 'Código recebido com sucesso.', linhas: 1, caracteres: c.length });
    },
  });
  t.digitar('int a;');
  await t.clicar();
  assert.match(t.resultado.textContent, /Falha de comunicação/);
  falhar = false;
  await t.clicar();
  assert.ok(t.resultado.classList.contains('resultado--sucesso'));
});

test('regressão: erro de entrada seguido de código válido', async () => {
  const t = await montar();
  t.digitar('   ');
  await t.clicar();
  assert.ok(t.resultado.classList.contains('resultado--aviso'));
  t.digitar('int a = 1;');
  await t.clicar();
  assert.ok(t.resultado.classList.contains('resultado--sucesso'));
});

test('mensagens do servidor são exibidas como texto (sem interpretar HTML)', async () => {
  const t = await montar({
    '/api/analisar': () => resposta(400, { recebido: false, erro: 'x', mensagem: '<img src=x onerror=alert(1)>' }),
  });
  t.digitar('int a;');
  await t.clicar();
  assert.equal(t.resultado.querySelector('img'), null);
  assert.match(t.resultado.textContent, /<img src=x/);
});

/* ======================= Outras interações ======================= */
test('Ctrl+Enter aciona a análise', async () => {
  const t = await montar();
  t.digitar('int a;');
  t.entrada.dispatchEvent(new t.dom.window.KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true, bubbles: true }));
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  assert.equal(t.fetch.analises().length, 1);
});

test('Limpar apaga o código, reseta o seletor e o resultado', async () => {
  const t = await montar();
  t.escolher('e1');
  await t.clicar();
  t.limpar.click();
  assert.equal(t.entrada.value, '');
  assert.equal(t.seletor.value, '');
  assert.ok(t.resultado.classList.contains('resultado--vazio'));
  assert.match(t.contador.textContent, /0 linhas/);
});
