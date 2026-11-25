/* Lógica da interface do Analisador Educacional.
 *
 * Organização:
 *  - validarEntrada: validação local (não substitui a do backend)
 *  - criarCliente: comunicação HTTP com o backend, com classificação de falhas
 *  - iniciar: liga a lógica aos elementos da página
 *  - visual.js: exibição didática dos tokens, erros e passo a passo (Etapa 3)
 *  - arvore.js: análise sintática, AST navegável e construção passo a passo (Etapa 4)
 * O arquivo funciona no navegador e também em Node (testes com jsdom).
 */
(function (raiz, fabrica) {
  if (typeof module === 'object' && module.exports) {
    module.exports = fabrica();
  } else {
    raiz.AnalisadorApp = fabrica();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // No Node (testes) carrega o módulo; no navegador usa o global criado por visual.js.
  var Visual = (typeof module === 'object' && typeof require === 'function')
    ? require('./visual.js')
    : (typeof AnalisadorVisual !== 'undefined' ? AnalisadorVisual : null);

  var Arvore = (typeof module === 'object' && typeof require === 'function')
    ? require('./arvore.js')
    : (typeof AnalisadorArvore !== 'undefined' ? AnalisadorArvore : null);

  var MENSAGENS = {
    vazio: 'Informe um código-fonte antes de solicitar a análise.',
    espacos: 'O código informado contém apenas espaços em branco. Digite um programa para analisar.',
    comunicacao: 'Não foi possível comunicar com o servidor. Verifique a conexão e tente novamente.',
    inesperado: 'Ocorreu um erro inesperado. Tente novamente em instantes.',
    exemplos: 'Não foi possível carregar os exemplos. Você ainda pode digitar seu próprio código.',
    proximasEtapas: 'A análise semântica será adicionada na próxima etapa.'
  };

  var TEMPO_LIMITE_MS = 10000;

  function validarEntrada(texto) {
    if (typeof texto !== 'string' || texto === '') {
      return { ok: false, erro: 'codigo_vazio', mensagem: MENSAGENS.vazio };
    }
    if (texto.trim() === '') {
      return { ok: false, erro: 'codigo_somente_espacos', mensagem: MENSAGENS.espacos };
    }
    return { ok: true };
  }

  function contar(texto) {
    var linhas = texto === '' ? 0 : texto.split(/\r\n|\r|\n/).length;
    if (texto.endsWith('\n')) linhas -= 1;
    return { linhas: linhas, caracteres: texto.length };
  }

  /* ---------- Comunicação com o backend ---------- */
  function criarCliente(fetchImpl, base) {
    base = base || '';

    async function requisitar(caminho, opcoes) {
      var controle = new AbortController();
      var timer = setTimeout(function () { controle.abort(); }, TEMPO_LIMITE_MS);
      try {
        opcoes.signal = controle.signal;
        return await fetchImpl(base + caminho, opcoes);
      } finally {
        clearTimeout(timer);
      }
    }

    async function lerJson(resposta) {
      try { return await resposta.json(); } catch (e) { return null; }
    }

    async function analisar(codigo) {
      var resposta;
      try {
        resposta = await requisitar('/api/analisar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ codigo: codigo })
        });
      } catch (e) {
        return { tipo: 'comunicacao', mensagem: MENSAGENS.comunicacao };
      }

      // Servidor ou proxy indisponível
      if ([502, 503, 504].indexOf(resposta.status) !== -1) {
        return { tipo: 'comunicacao', mensagem: MENSAGENS.comunicacao };
      }

      var dados = await lerJson(resposta);

      if (resposta.ok && dados && dados.recebido === true) {
        return { tipo: 'sucesso', dados: dados };
      }
      if ((resposta.status === 400 || resposta.status === 413) && dados && typeof dados.mensagem === 'string') {
        return { tipo: 'entrada', erro: dados.erro, mensagem: dados.mensagem };
      }
      return { tipo: 'inesperado', mensagem: MENSAGENS.inesperado };
    }

    async function listarExemplos() {
      try {
        var resposta = await requisitar('/api/exemplos', { method: 'GET' });
        if (!resposta.ok) return { tipo: 'inesperado', mensagem: MENSAGENS.exemplos };
        var dados = await lerJson(resposta);
        if (!dados || !Array.isArray(dados.exemplos)) {
          return { tipo: 'inesperado', mensagem: MENSAGENS.exemplos };
        }
        return { tipo: 'sucesso', exemplos: dados.exemplos };
      } catch (e) {
        return { tipo: 'comunicacao', mensagem: MENSAGENS.exemplos };
      }
    }

    async function obterGramatica() {
      try {
        var resposta = await requisitar('/api/gramatica', { method: 'GET' });
        if (!resposta.ok) return null;
        var dados = await lerJson(resposta);
        return dados && typeof dados.ebnf === 'string' ? dados : null;
      } catch (e) {
        return null;
      }
    }

    return { analisar: analisar, listarExemplos: listarExemplos, obterGramatica: obterGramatica };
  }

  /* ---------- Interface ---------- */
  function iniciar(doc, fetchImpl, base) {
    var cliente = criarCliente(fetchImpl, base);
    var entrada = doc.getElementById('entrada-codigo');
    var botao = doc.getElementById('btn-analisar');
    var limpar = doc.getElementById('btn-limpar');
    var seletor = doc.getElementById('seletor-exemplos');
    var descricao = doc.getElementById('descricao-exemplo');
    var resultado = doc.getElementById('resultado');
    var contador = doc.getElementById('contador');
    var exemplos = [];
    var ocupado = false;
    var passoAPasso = null;
    var arvore = null;

    function el(tag, classe, texto) {
      var e = doc.createElement(tag);
      if (classe) e.className = classe;
      if (texto !== undefined) e.textContent = texto; // nunca innerHTML: evita injeção de HTML
      return e;
    }

    function mostrar(classe, titulo, mensagem, extras) {
      resultado.className = 'resultado ' + classe;
      resultado.textContent = '';
      if (titulo) resultado.appendChild(el('p', 'resultado__titulo', titulo));
      if (mensagem) resultado.appendChild(el('p', 'resultado__mensagem', mensagem));
      (extras || []).forEach(function (x) { resultado.appendChild(x); });
    }

    function esconderAnalise() {
      if (Visual) Visual.esconderAnalise(doc, passoAPasso);
      passoAPasso = null;
      if (Arvore) Arvore.esconder(doc, arvore);
      arvore = null;
    }

    function atualizarContador() {
      var c = contar(entrada.value);
      contador.textContent = c.linhas + (c.linhas === 1 ? ' linha' : ' linhas') +
        ' · ' + c.caracteres + (c.caracteres === 1 ? ' caractere' : ' caracteres');
    }

    function definirOcupado(valor) {
      ocupado = valor;
      botao.disabled = valor;
      botao.textContent = valor ? 'Analisando…' : 'Analisar código';
    }

    async function analisar() {
      if (ocupado) return;
      var codigo = entrada.value;

      var v = validarEntrada(codigo);
      if (!v.ok) {
        esconderAnalise();
        mostrar('resultado--aviso', 'Entrada inválida', v.mensagem);
        entrada.focus();
        return;
      }

      definirOcupado(true);
      mostrar('resultado--carregando', null, 'Enviando o código para o servidor…');
      try {
        var r = await cliente.analisar(codigo);
        if (r.tipo === 'sucesso') {
          var d = r.dados;
          var comErros = d.sucesso === false;
          mostrar(comErros ? 'resultado--aviso' : 'resultado--sucesso',
            d.mensagem || 'Código recebido com sucesso.',
            d.linhas + (d.linhas === 1 ? ' linha' : ' linhas') + ' · ' + d.caracteres +
            (d.caracteres === 1 ? ' caractere' : ' caracteres'),
            [el('p', 'resultado__nota', MENSAGENS.proximasEtapas)]);
          esconderAnalise();
          if (Visual && Array.isArray(d.tokens)) {
            passoAPasso = Visual.mostrarAnalise(doc, codigo, d);
            if (Arvore) arvore = Arvore.mostrarSintatico(doc, codigo, d);
          }
        } else if (r.tipo === 'entrada') {
          esconderAnalise();
          mostrar('resultado--aviso', 'Entrada inválida', r.mensagem);
        } else if (r.tipo === 'comunicacao') {
          esconderAnalise();
          mostrar('resultado--erro', 'Falha de comunicação', r.mensagem);
        } else {
          esconderAnalise();
          mostrar('resultado--erro', 'Erro inesperado', r.mensagem);
        }
      } catch (e) {
        esconderAnalise();
        mostrar('resultado--erro', 'Erro inesperado', MENSAGENS.inesperado);
      } finally {
        definirOcupado(false); // a interface nunca fica travada
      }
    }

    function aoSelecionarExemplo() {
      var id = seletor.value;
      var ex = exemplos.filter(function (x) { return x.id === id; })[0];
      if (!ex) { descricao.textContent = 'Escolha um exemplo ou escreva o seu próprio programa abaixo.'; return; }
      entrada.value = ex.codigo; // substitui o conteúdo anterior; continua editável
      descricao.textContent = ex.descricao;
      atualizarContador();
    }

    function aoLimpar() {
      entrada.value = '';
      seletor.value = '';
      descricao.textContent = 'Escolha um exemplo ou escreva o seu próprio programa abaixo.';
      esconderAnalise();
      resultado.className = 'resultado resultado--vazio';
      resultado.textContent = 'O resultado aparecerá aqui depois que você clicar em Analisar código.';
      atualizarContador();
      entrada.focus();
    }

    async function carregarExemplos() {
      var r = await cliente.listarExemplos();
      if (r.tipo !== 'sucesso') {
        mostrar('resultado--aviso', 'Exemplos indisponíveis', r.mensagem);
        return;
      }
      exemplos = r.exemplos;
      exemplos.forEach(function (ex) {
        var o = el('option', '', ex.titulo);
        o.value = ex.id;
        seletor.appendChild(o);
      });
    }

    botao.addEventListener('click', analisar);
    limpar.addEventListener('click', aoLimpar);
    seletor.addEventListener('change', aoSelecionarExemplo);
    entrada.addEventListener('input', atualizarContador);
    entrada.addEventListener('keydown', function (ev) {
      if ((ev.ctrlKey || ev.metaKey) && ev.key === 'Enter') { ev.preventDefault(); analisar(); }
    });

    async function carregarGramatica() {
      var alvo = doc.getElementById('gramatica-ebnf');
      if (!alvo || !Arvore) return;
      var g = await cliente.obterGramatica();
      if (g) Arvore.renderGramatica(doc, alvo, g);
      else alvo.textContent = 'A gramática não pôde ser carregada agora (veja docs/gramatica.md).';
    }

    var legenda = doc.getElementById('legenda-categorias');
    if (Visual && legenda) Visual.renderLegenda(doc, legenda);

    atualizarContador();
    return {
      pronto: Promise.all([carregarExemplos(), carregarGramatica()]),
      analisar: analisar,
      passoAPasso: function () { return passoAPasso; },
      arvore: function () { return arvore; }
    };
  }

  var api = { validarEntrada: validarEntrada, contar: contar, criarCliente: criarCliente, iniciar: iniciar, MENSAGENS: MENSAGENS };

  if (typeof document !== 'undefined' && typeof module === 'undefined') {
    document.addEventListener('DOMContentLoaded', function () {
      iniciar(document, window.fetch.bind(window));
    });
  }
  return api;
}));
