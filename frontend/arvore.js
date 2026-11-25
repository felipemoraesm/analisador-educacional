/* Visualização da análise sintática (Etapa 4).
 *
 * Recebe `dados.sintatico` do backend e monta:
 *  - o status da análise sintática e a lista de erros sintáticos (com a regra violada);
 *  - a AST como árvore navegável (nós expansíveis, filtro por tipo, destaque do
 *    trecho no código, detalhes com a regra gramatical e os tokens do nó);
 *  - a construção da árvore passo a passo, na ordem em que o parser reconhece os nós;
 *  - a versão em texto (acessível) e a exportação em JSON.
 *
 * Todo texto vindo do servidor é inserido com textContent (nunca innerHTML).
 * Funciona no navegador e em Node (testes com jsdom).
 */
(function (raiz, fabrica) {
  if (typeof module === 'object' && module.exports) {
    module.exports = fabrica();
  } else {
    raiz.AnalisadorArvore = fabrica();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // No Node (testes) carrega o módulo; no navegador usa o global criado por visual.js.
  var Visual = (typeof module === 'object' && typeof require === 'function')
    ? require('./visual.js')
    : (typeof AnalisadorVisual !== 'undefined' ? AnalisadorVisual : null);

  var VELOCIDADES = { lenta: 1000, normal: 500, rapida: 150 };
  var LIMITE_EXPANDIR_TUDO = 3000;
  var LIMITE_TOKENS_NO = 40;
  var ROTULO_CATEGORIA = {
    estrutura: 'estrutura', declaracao: 'declaração', controle: 'controle de fluxo',
    expressao: 'expressão', folha: 'folha'
  };
  // Símbolos distintos por categoria: a informação não depende só da cor (acessibilidade)
  var SIMBOLO_CATEGORIA = { estrutura: '▣', declaracao: '◆', controle: '↻', expressao: 'ƒ', folha: '●' };

  function el(doc, tag, classe, texto) {
    var e = doc.createElement(tag);
    if (classe) e.className = classe;
    if (texto !== undefined && texto !== null) e.textContent = texto;
    return e;
  }
  function limpar(no) { while (no.firstChild) no.removeChild(no.firstChild); }
  function plural(n, s, p) { return n + ' ' + (n === 1 ? s : p); }

  /* ---------- Mensagens e rótulos ---------- */
  function mensagemErroSintatico(e) {
    var m = String(e.mensagem || 'Erro sintático');
    m = m.charAt(0).toLowerCase() + m.slice(1);
    return 'Erro sintático na linha ' + e.linha + ', coluna ' + e.coluna + ': ' + m;
  }

  function descreverAtributos(no) {
    var partes = [];
    var a = no.atributos || {};
    Object.keys(a).forEach(function (k) { partes.push(k + '=' + a[k]); });
    return partes.join(', ');
  }

  function categoriaDe(tipo, regras) {
    return (regras && regras[tipo] && regras[tipo].categoria) || 'expressao';
  }

  /* ---------- Status e erros sintáticos ---------- */
  function renderErrosSintaticos(doc, cont, erros, truncado) {
    limpar(cont);
    erros = erros || [];
    if (erros.length === 0) return;
    var lista = el(doc, 'ol', 'erros__lista');
    erros.forEach(function (e) {
      var li = el(doc, 'li', 'erro-item erro-item--sint');
      li.appendChild(el(doc, 'strong', null, mensagemErroSintatico(e).split(': ')[0] + ': '));
      var corpo = mensagemErroSintatico(e);
      li.appendChild(doc.createTextNode(corpo.slice(corpo.indexOf(': ') + 2)));
      if (e.esperado && e.esperado.length) {
        var esp = el(doc, 'span', 'erro-item__extra', 'Esperado: ');
        esp.appendChild(el(doc, 'code', null, e.esperado.join('  ')));
        li.appendChild(esp);
      }
      if (e.regra) {
        var reg = el(doc, 'span', 'erro-item__extra', 'Regra da gramática: ');
        reg.appendChild(el(doc, 'code', null, e.regra));
        li.appendChild(reg);
      }
      if (e.dica) li.appendChild(el(doc, 'span', 'erro-item__dica', e.dica));
      lista.appendChild(li);
    });
    cont.appendChild(lista);
    if (truncado) {
      cont.appendChild(el(doc, 'p', 'ajuda', 'Mostrando apenas os primeiros erros: corrija-os e analise de novo.'));
    }
  }

  function mostrarStatus(doc, cont, classe, titulo, mensagem) {
    cont.className = 'resultado ' + classe;
    limpar(cont);
    cont.appendChild(el(doc, 'p', 'resultado__titulo', titulo));
    if (mensagem) cont.appendChild(el(doc, 'p', 'resultado__mensagem', mensagem));
  }

  /* ---------- A árvore ---------- */
  function criarArvore(doc, codigo, sint, dados, opcoes) {
    opcoes = opcoes || {};
    var agendar = opcoes.agendar || function (fn, ms) { return setTimeout(fn, ms); };
    var cancelar = opcoes.cancelar || function (h) { clearTimeout(h); };
    var baixar = opcoes.baixar || function (nome, texto) {
      var w = doc.defaultView;
      if (!w || !w.URL || !w.URL.createObjectURL) return;
      var url = w.URL.createObjectURL(new w.Blob([texto], { type: 'application/json' }));
      var a = doc.createElement('a');
      a.href = url; a.download = nome;
      doc.body.appendChild(a); a.click(); doc.body.removeChild(a);
      w.URL.revokeObjectURL(url);
    };
    var $ = function (id) { return doc.getElementById(id); };
    var ui = {
      arvore: $('ast-arvore'), codigo: $('ast-codigo'), detalhes: $('ast-detalhes'), resumo: $('ast-resumo'),
      texto: $('ast-texto'), filtro: $('ast-filtro'), expandir: $('ast-expandir'), recolher: $('ast-recolher'),
      exportar: $('ast-exportar'), narracao: $('ast-narracao'), info: $('ast-passo-info'),
      inicio: $('ast-passo-inicio'), anterior: $('ast-passo-anterior'), proximo: $('ast-passo-proximo'),
      fim: $('ast-passo-fim'), tocar: $('ast-passo-reproduzir'), velocidade: $('ast-passo-velocidade')
    };
    var ast = sint.ast;
    var regras = sint.regras || {};
    var tokens = (dados && dados.tokens) || [];

    // ----- índices -----
    var porId = {}, paiDe = {}, nivelDe = {}, posOrdem = {}, ordem = [];
    (function indexar(no, pai, nivel) {
      porId[no.id] = no;
      paiDe[no.id] = pai ? pai.id : null;
      nivelDe[no.id] = nivel;
      no.filhos.forEach(function (f) { indexar(f, no, nivel + 1); });
      ordem.push(no.id);
      posOrdem[no.id] = ordem.length;
    }(ast, null, 1));
    var N = ordem.length;
    var tipos = {};
    ordem.forEach(function (id) { tipos[porId[id].tipo] = true; });

    var itens = {};       // id -> <li> já criado
    var selecionado = null;
    var idx = N;          // quantos nós já foram "construídos" (N = árvore completa)
    var iniciou = false;  // o usuário já mexeu nos controles da construção?
    var tocando = false, timer = null;
    var ouvintes = [];

    function trecho(no) { return codigo.slice(no.inicio, no.fim); }
    function infoCategoria(no) {
      var cat = categoriaDe(no.tipo, regras);
      return { chave: cat, rotulo: ROTULO_CATEGORIA[cat] || cat, simbolo: SIMBOLO_CATEGORIA[cat] || '•' };
    }

    // ----- DOM da árvore (filhos criados sob demanda) -----
    function criarItem(no) {
      var cat = infoCategoria(no);
      var li = el(doc, 'li', 'ast-no');
      li.setAttribute('role', 'treeitem');
      li.setAttribute('aria-level', String(nivelDe[no.id]));
      li.setAttribute('aria-selected', 'false');
      li.dataset.id = String(no.id);
      li.dataset.tipo = no.tipo;
      var linha = el(doc, 'div', 'ast-no__linha');
      if (no.filhos.length > 0) {
        li.setAttribute('aria-expanded', 'false');
        var t = el(doc, 'button', 'ast-toggle', '▸');
        t.type = 'button';
        t.setAttribute('aria-label', 'Expandir ou recolher ' + no.tipo);
        t.addEventListener('click', function () { alternar(no.id); });
        linha.appendChild(t);
      } else {
        linha.appendChild(el(doc, 'span', 'ast-toggle ast-toggle--vazio', ''));
      }
      var rot = el(doc, 'button', 'ast-no__rotulo ast-cat-' + cat.chave);
      rot.type = 'button';
      if (no.papel) rot.appendChild(el(doc, 'span', 'ast-no__papel', no.papel + ':'));
      rot.appendChild(el(doc, 'span', 'ast-no__simbolo', cat.simbolo));
      rot.appendChild(el(doc, 'span', 'ast-no__tipo', no.tipo));
      var attrs = descreverAtributos(no);
      if (attrs) rot.appendChild(el(doc, 'span', 'ast-no__attrs', '(' + attrs + ')'));
      rot.appendChild(el(doc, 'small', 'ast-no__cat', cat.rotulo));
      rot.addEventListener('click', function () { selecionar(no.id); });
      linha.appendChild(rot);
      li.appendChild(linha);
      itens[no.id] = li;
      aplicarEstado(li, no);
      return li;
    }

    function aplicarEstado(li, no) {
      li.classList.toggle('ast-no--fantasma', posOrdem[no.id] > idx);
      li.classList.toggle('ast-no--atual', iniciou && idx > 0 && ordem[idx - 1] === no.id);
      var filtro = ui.filtro ? ui.filtro.value : '';
      li.classList.toggle('ast-no--filtrado', !!filtro && no.tipo !== filtro);
      li.classList.toggle('ast-no--destaque', !!filtro && no.tipo === filtro);
    }

    function temGrupo(li) {
      for (var k = 0; k < li.children.length; k++) if (li.children[k].tagName === 'UL') return true;
      return false;
    }

    function criarFilhos(li, no) {
      if (temGrupo(li)) return;
      var ul = el(doc, 'ul', 'ast-grupo');
      ul.setAttribute('role', 'group');
      no.filhos.forEach(function (f) { ul.appendChild(criarItem(f)); });
      li.appendChild(ul);
    }

    function expandir(id) {
      var no = porId[id], li = itens[id];
      if (!li || no.filhos.length === 0) return;
      criarFilhos(li, no);
      li.setAttribute('aria-expanded', 'true');
      li.querySelector('.ast-toggle').textContent = '▾';
    }
    function recolherNo(id) {
      var li = itens[id];
      if (!li || porId[id].filhos.length === 0) return;
      li.setAttribute('aria-expanded', 'false');
      li.querySelector('.ast-toggle').textContent = '▸';
    }
    function alternar(id) {
      var li = itens[id];
      if (li.getAttribute('aria-expanded') === 'true') recolherNo(id); else expandir(id);
    }
    function revelar(id) {
      var cadeia = [];
      for (var p = paiDe[id]; p !== null; p = paiDe[p]) cadeia.unshift(p);
      cadeia.forEach(expandir);
    }
    function expandirTudo() {
      var limite = N > LIMITE_EXPANDIR_TUDO ? 6 : Infinity;
      (function rec(no) {
        if (nivelDe[no.id] > limite) return;
        expandir(no.id);
        no.filhos.forEach(rec);
      }(ast));
    }
    function recolherTudo() {
      Object.keys(itens).forEach(function (id) { if (Number(id) !== ast.id) recolherNo(Number(id)); });
      expandir(ast.id);
    }

    // ----- seleção, código e detalhes -----
    function renderCodigo(no) {
      limpar(ui.codigo);
      if (!no) { ui.codigo.appendChild(doc.createTextNode(codigo)); return; }
      if (no.inicio > 0) ui.codigo.appendChild(el(doc, 'span', 'passo-lido', codigo.slice(0, no.inicio)));
      ui.codigo.appendChild(el(doc, 'span', 'ast-sel', codigo.slice(no.inicio, no.fim)));
      if (no.fim < codigo.length) ui.codigo.appendChild(el(doc, 'span', 'passo-resto', codigo.slice(no.fim)));
    }

    function linhaDetalhe(rotulo, valor, codigoFmt) {
      var p = el(doc, 'p', 'ast-det');
      p.appendChild(el(doc, 'strong', null, rotulo + ': '));
      p.appendChild(codigoFmt ? el(doc, 'code', null, valor) : doc.createTextNode(valor));
      return p;
    }

    function renderDetalhes(no) {
      limpar(ui.detalhes);
      if (!no) {
        ui.detalhes.appendChild(el(doc, 'p', 'ajuda', 'Selecione um nó da árvore para ver sua regra gramatical, posição e tokens.'));
        return;
      }
      var cat = infoCategoria(no);
      var meta = regras[no.tipo] || {};
      ui.detalhes.appendChild(linhaDetalhe('Nó', no.tipo + ' (' + cat.rotulo + ')'));
      if (meta.descricao) ui.detalhes.appendChild(linhaDetalhe('O que é', meta.descricao));
      if (meta.regra) ui.detalhes.appendChild(linhaDetalhe('Regra gramatical', meta.regra, true));
      var attrs = descreverAtributos(no);
      ui.detalhes.appendChild(linhaDetalhe('Atributos', attrs || '(nenhum)'));
      if (no.papel) ui.detalhes.appendChild(linhaDetalhe('Papel no nó pai', no.papel + (paiDe[no.id] ? ' de ' + porId[paiDe[no.id]].tipo : '')));
      ui.detalhes.appendChild(linhaDetalhe('Posição', 'linha ' + no.linha + ', coluna ' + no.coluna +
        ' até linha ' + no.fim_linha + ', coluna ' + no.fim_coluna));
      ui.detalhes.appendChild(linhaDetalhe('Trecho do código', trecho(no), true));
      var dentro = tokens.filter(function (t) { return t.inicio >= no.inicio && t.fim <= no.fim; });
      var p = el(doc, 'p', 'ast-det');
      p.appendChild(el(doc, 'strong', null, 'Tokens deste nó (' + dentro.length + '): '));
      var chips = el(doc, 'span', 'chips');
      dentro.slice(0, LIMITE_TOKENS_NO).forEach(function (t) {
        var c = Visual ? Visual.categoria(t.tipo) : { curto: t.tipo, css: 'tk-outro' };
        chips.appendChild(el(doc, 'span', 'seq-item tk ' + c.css, '<' + c.curto + ', ' + t.lexema + '>'));
      });
      if (dentro.length > LIMITE_TOKENS_NO) chips.appendChild(el(doc, 'span', 'seq-mais', '… e mais ' + (dentro.length - LIMITE_TOKENS_NO)));
      p.appendChild(chips);
      ui.detalhes.appendChild(p);
    }

    function selecionar(id) {
      if (selecionado !== null && itens[selecionado]) {
        itens[selecionado].classList.remove('ast-no--sel');
        itens[selecionado].setAttribute('aria-selected', 'false');
      }
      selecionado = id;
      if (id === null) { renderCodigo(null); renderDetalhes(null); return; }
      revelar(id);
      var li = itens[id];
      li.classList.add('ast-no--sel');
      li.setAttribute('aria-selected', 'true');
      renderCodigo(porId[id]);
      renderDetalhes(porId[id]);
    }

    // ----- filtro -----
    function aplicarFiltro() {
      var filtro = ui.filtro.value;
      if (filtro) {
        ordem.forEach(function (id) { if (porId[id].tipo === filtro) revelar(id); });
      }
      Object.keys(itens).forEach(function (id) { aplicarEstado(itens[id], porId[id]); });
    }

    // ----- construção passo a passo -----
    function narrar() {
      if (idx === N && !iniciou) {
        return 'A árvore está completa. Use Início e Próximo para ver a ordem em que o parser a constrói: ' +
          'dos nós mais internos (as folhas) até a raiz.';
      }
      if (idx === 0) return 'Nenhum nó foi reconhecido ainda. Clique em Próximo: o parser começa pelas folhas.';
      var no = porId[ordem[idx - 1]];
      var meta = regras[no.tipo] || {};
      var txt = 'Passo ' + idx + ' de ' + N + ': o parser terminou de reconhecer ' + no.tipo;
      var attrs = descreverAtributos(no);
      if (attrs) txt += ' (' + attrs + ')';
      txt += ', que corresponde ao trecho "' + trecho(no) + '".';
      if (no.filhos.length === 0) {
        txt += ' É uma folha: vem diretamente de um único token.';
      } else {
        txt += ' Ele combina ' + plural(no.filhos.length, 'filho já pronto', 'filhos já prontos') + ': ' +
          no.filhos.map(function (f) { return f.tipo; }).join(', ') + '.';
      }
      if (meta.regra) txt += ' Regra usada: ' + meta.regra;
      if (idx === N) txt += ' Este é o último passo: a raiz foi construída e a árvore está completa.';
      return txt;
    }

    function atualizarConstrucao() {
      Object.keys(itens).forEach(function (id) { aplicarEstado(itens[id], porId[id]); });
      ui.narracao.textContent = narrar();
      ui.info.textContent = 'Passo ' + idx + ' de ' + N;
      ui.inicio.disabled = idx === 0;
      ui.anterior.disabled = idx === 0;
      ui.proximo.disabled = idx === N;
      ui.fim.disabled = idx === N;
      ui.tocar.textContent = tocando ? '⏸ Pausar' : '▶ Reproduzir';
      ui.tocar.setAttribute('aria-pressed', tocando ? 'true' : 'false');
    }

    function irPara(i) {
      iniciou = true;
      idx = Math.max(0, Math.min(N, i));
      if (idx > 0) selecionar(ordem[idx - 1]); else selecionar(null);
      atualizarConstrucao();
    }
    function pausar() {
      tocando = false;
      if (timer !== null) { cancelar(timer); timer = null; }
      atualizarConstrucao();
    }
    function agendarProximo() {
      var ms = VELOCIDADES[ui.velocidade ? ui.velocidade.value : 'normal'] || VELOCIDADES.normal;
      timer = agendar(function () {
        timer = null;
        if (!tocando) return;
        irPara(idx + 1);
        if (idx >= N) pausar(); else agendarProximo();
      }, ms);
    }
    function reproduzir() {
      if (idx >= N) irPara(0);
      tocando = true;
      atualizarConstrucao();
      agendarProximo();
    }

    // ----- exportação -----
    function exportarJson() { return JSON.stringify(ast, null, 2); }

    // ----- inicialização -----
    limpar(ui.arvore);
    ui.arvore.appendChild(criarItem(ast));
    if (N <= 150) expandirTudo();
    else {
      (function rec(no) { if (nivelDe[no.id] <= 3) { expandir(no.id); no.filhos.forEach(rec); } }(ast));
    }

    limpar(ui.filtro);
    var op = el(doc, 'option', null, 'Todos os tipos');
    op.value = '';
    ui.filtro.appendChild(op);
    Object.keys(tipos).sort().forEach(function (t) { var o = el(doc, 'option', null, t); o.value = t; ui.filtro.appendChild(o); });

    var altura = sint.resumo ? sint.resumo.altura : 0;
    ui.resumo.textContent = plural(N, 'nó', 'nós') + ' · altura ' + altura +
      (N > LIMITE_EXPANDIR_TUDO ? ' · árvore grande: "Expandir tudo" abre só os 6 primeiros níveis' : '');
    ui.texto.textContent = sint.texto || 'A árvore é grande demais para a versão em texto. Use a árvore interativa ou exporte o JSON.';
    renderCodigo(null);
    renderDetalhes(null);
    atualizarConstrucao();

    function ligar(no, tipo, fn) { no.addEventListener(tipo, fn); ouvintes.push([no, tipo, fn]); }
    ligar(ui.expandir, 'click', expandirTudo);
    ligar(ui.recolher, 'click', recolherTudo);
    ligar(ui.filtro, 'change', aplicarFiltro);
    ligar(ui.exportar, 'click', function () { baixar('ast.json', exportarJson()); });
    ligar(ui.inicio, 'click', function () { pausar(); irPara(0); });
    ligar(ui.anterior, 'click', function () { pausar(); irPara(idx - 1); });
    ligar(ui.proximo, 'click', function () { pausar(); irPara(idx + 1); });
    ligar(ui.fim, 'click', function () { pausar(); irPara(N); });
    ligar(ui.tocar, 'click', function () { if (tocando) pausar(); else reproduzir(); });
    ligar(ui.velocidade, 'change', function () { if (tocando) { if (timer !== null) cancelar(timer); agendarProximo(); } });

    function destruir() {
      tocando = false;
      if (timer !== null) { cancelar(timer); timer = null; }
      ouvintes.forEach(function (o) { o[0].removeEventListener(o[1], o[2]); });
      ouvintes = [];
    }

    return {
      total: function () { return N; }, indice: function () { return idx; }, ordem: ordem,
      selecionar: selecionar, selecionado: function () { return selecionado; },
      expandirTudo: expandirTudo, recolherTudo: recolherTudo, irPara: irPara, reproduzir: reproduzir,
      pausar: pausar, estaTocando: function () { return tocando; }, exportarJson: exportarJson,
      destruir: destruir
    };
  }

  /* ---------- Orquestração ---------- */
  function esconder(doc, controle) {
    if (controle) controle.destruir();
    var s = doc.getElementById('secao-ast');
    if (s) s.hidden = true;
    var st = doc.getElementById('sintatico-status');
    if (st) { st.className = 'resultado resultado--vazio'; limpar(st); }
    var er = doc.getElementById('erros-sintaticos');
    if (er) limpar(er);
  }

  function mostrarSintatico(doc, codigo, dados, opcoes) {
    var sint = dados && dados.sintatico;
    var status = doc.getElementById('sintatico-status');
    var erros = doc.getElementById('erros-sintaticos');
    var secao = doc.getElementById('secao-ast');
    if (!sint) { esconder(doc, null); return null; }  // resposta antiga (sem análise sintática)

    renderErrosSintaticos(doc, erros, sint.erros, sint.erros_truncados);

    if (!sint.executado) {
      secao.hidden = true;
      mostrarStatus(doc, status, 'resultado--aviso', 'Análise sintática não executada', sint.motivo || sint.mensagem);
      return null;
    }
    if (!sint.sucesso) {
      secao.hidden = true;
      mostrarStatus(doc, status, 'resultado--aviso',
        'Erros sintáticos: ' + plural((sint.erros || []).length, 'erro encontrado', 'erros encontrados'),
        'A árvore (AST) não foi construída. Corrija os erros abaixo; a gramática violada aparece em cada um.');
      return null;
    }
    mostrarStatus(doc, status, 'resultado--sucesso', 'Análise sintática concluída', sint.mensagem);
    secao.hidden = false;
    return criarArvore(doc, codigo, sint, dados, opcoes);
  }

  function renderGramatica(doc, pre, dados) {
    pre.textContent = dados.ebnf;
  }

  return {
    mostrarSintatico: mostrarSintatico, esconder: esconder, criarArvore: criarArvore,
    mensagemErroSintatico: mensagemErroSintatico, descreverAtributos: descreverAtributos,
    renderErrosSintaticos: renderErrosSintaticos, renderGramatica: renderGramatica,
    VELOCIDADES: VELOCIDADES
  };
}));
