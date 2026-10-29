/* Visualização didática da análise léxica.
 *
 * Recebe a resposta do backend (tokens, erros, comentários, resumo) e monta:
 *  - resumo por categoria e lista de erros léxicos;
 *  - código colorido por categoria;
 *  - sequência de tokens (<categoria, lexema>);
 *  - tabela de tokens;
 *  - "passo a passo": o scanner lendo o código caractere a caractere, com os
 *    estados do autômato, controles de avançar/voltar e reprodução automática.
 *
 * Todo texto vindo do servidor é inserido com textContent (nunca innerHTML).
 * Funciona no navegador e em Node (testes com jsdom).
 */
(function (raiz, fabrica) {
  if (typeof module === 'object' && module.exports) {
    module.exports = fabrica();
  } else {
    raiz.AnalisadorVisual = fabrica();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var LIMITE_TABELA = 2000;
  var LIMITE_SEQUENCIA = 400;
  var LIMITE_TRANSICOES = 30;
  var LIMITE_EMITIDOS = 12;
  var VELOCIDADES = { lenta: 900, normal: 450, rapida: 120 };

  var CATEGORIAS = [
    { tipo: 'PALAVRA_RESERVADA', rotulo: 'Palavra reservada', curto: 'RESERV', css: 'tk-reservada',
      exemplos: 'int, float, char, if, else, while, return',
      descricao: 'Palavra com significado fixo na linguagem; não pode ser usada como nome.' },
    { tipo: 'IDENTIFICADOR', rotulo: 'Identificador', curto: 'ID', css: 'tk-identificador',
      exemplos: 'numero, _x1, total2',
      descricao: 'Nome dado pelo programador a variáveis. Começa com letra ou _, seguido de letras, dígitos ou _.' },
    { tipo: 'LITERAL_INTEIRO', rotulo: 'Literal inteiro', curto: 'INT', css: 'tk-inteiro',
      exemplos: '0, 42, 1000', descricao: 'Número sem parte fracionária.' },
    { tipo: 'LITERAL_REAL', rotulo: 'Literal real', curto: 'REAL', css: 'tk-real',
      exemplos: '3.14, 0.5', descricao: 'Número com ponto decimal e dígitos dos dois lados.' },
    { tipo: 'LITERAL_STRING', rotulo: 'Literal string', curto: 'STR', css: 'tk-string',
      exemplos: '"ola", "a\\n"', descricao: 'Texto entre aspas duplas, na mesma linha.' },
    { tipo: 'LITERAL_CHAR', rotulo: 'Literal caractere', curto: 'CHAR', css: 'tk-char',
      exemplos: "'a', '\\n'", descricao: 'Um único caractere entre apóstrofos.' },
    { tipo: 'OPERADOR_ARITMETICO', rotulo: 'Operador aritmético', curto: 'ARIT', css: 'tk-aritmetico',
      exemplos: '+  -  *  /  %', descricao: 'Operações matemáticas.' },
    { tipo: 'OPERADOR_RELACIONAL', rotulo: 'Operador relacional', curto: 'REL', css: 'tk-relacional',
      exemplos: '==  !=  <  >  <=  >=', descricao: 'Comparações entre valores.' },
    { tipo: 'OPERADOR_LOGICO', rotulo: 'Operador lógico', curto: 'LOG', css: 'tk-logico',
      exemplos: '&&  ||  !', descricao: 'Combinam ou invertem condições.' },
    { tipo: 'OPERADOR_ATRIBUICAO', rotulo: 'Operador de atribuição', curto: 'ATRIB', css: 'tk-atribuicao',
      exemplos: '=', descricao: 'Guarda um valor em uma variável.' },
    { tipo: 'DELIMITADOR', rotulo: 'Delimitador', curto: 'DELIM', css: 'tk-delimitador',
      exemplos: '( ) { } [ ] ; ,', descricao: 'Separam e agrupam partes do programa.' }
  ];
  var POR_TIPO = {};
  CATEGORIAS.forEach(function (c) { POR_TIPO[c.tipo] = c; });

  var NOMES_CLASSE = {
    letra: 'letra', digito: 'dígito', sublinhado: 'sublinhado', ponto: 'ponto',
    aspas: 'aspas', apostrofo: 'apóstrofo', barra_invertida: 'barra invertida', simbolo: 'símbolo'
  };

  function categoria(tipo) {
    return POR_TIPO[tipo] || { tipo: tipo, rotulo: tipo, curto: tipo, css: 'tk-outro', exemplos: '', descricao: '' };
  }

  function el(doc, tag, classe, texto) {
    var e = doc.createElement(tag);
    if (classe) e.className = classe;
    if (texto !== undefined && texto !== null) e.textContent = texto;
    return e;
  }

  function limpar(no) { while (no.firstChild) no.removeChild(no.firstChild); }

  function plural(n, singular, pluralTxt) { return n + ' ' + (n === 1 ? singular : pluralTxt); }

  /* ---------- Mensagens ---------- */
  function descricaoErro(e) {
    var m = String(e.mensagem || 'Erro léxico');
    m = m.charAt(0).toLowerCase() + m.slice(1);
    if (!/[.!?]$/.test(m)) m += '.';
    return m;
  }

  function mensagemErro(e) {
    var texto = 'Erro léxico na linha ' + e.linha + ', coluna ' + e.coluna + ': ' + descricaoErro(e);
    if (e.dica) texto += ' ' + e.dica;
    return texto;
  }

  /* ---------- Resumo, erros e legenda ---------- */
  function renderResumo(doc, cont, dados) {
    limpar(cont);
    var r = dados.resumo || { total_tokens: 0, total_erros: 0, total_comentarios: 0, por_categoria: {} };
    cont.appendChild(el(doc, 'p', 'resumo__linha',
      plural(r.total_tokens, 'token', 'tokens') + ' · ' +
      plural(r.total_erros, 'erro léxico', 'erros léxicos') + ' · ' +
      plural(r.total_comentarios, 'comentário ignorado', 'comentários ignorados')));
    var chips = el(doc, 'div', 'chips');
    CATEGORIAS.forEach(function (c) {
      var n = (r.por_categoria || {})[c.tipo];
      if (!n) return;
      var chip = el(doc, 'span', 'chip tk ' + c.css, c.rotulo + ' ');
      chip.appendChild(el(doc, 'strong', null, String(n)));
      chips.appendChild(chip);
    });
    cont.appendChild(chips);
  }

  function renderErros(doc, cont, erros) {
    limpar(cont);
    erros = erros || [];
    if (erros.length === 0) {
      cont.appendChild(el(doc, 'p', 'erros__vazio', 'Nenhum erro léxico encontrado.'));
      return;
    }
    var lista = el(doc, 'ol', 'erros__lista');
    erros.forEach(function (e) {
      var li = el(doc, 'li', 'erro-item');
      li.appendChild(el(doc, 'strong', null, 'Erro léxico na linha ' + e.linha + ', coluna ' + e.coluna + ': '));
      li.appendChild(doc.createTextNode(descricaoErro(e)));
      if (e.dica) li.appendChild(el(doc, 'span', 'erro-item__dica', ' ' + e.dica));
      lista.appendChild(li);
    });
    cont.appendChild(lista);
  }

  function renderLegenda(doc, cont) {
    limpar(cont);
    var tabela = el(doc, 'table', 'tabela tabela--legenda');
    var cab = el(doc, 'thead');
    var tr = el(doc, 'tr');
    ['Categoria', 'Exemplos', 'O que é'].forEach(function (t) { tr.appendChild(el(doc, 'th', null, t)); });
    cab.appendChild(tr);
    tabela.appendChild(cab);
    var corpo = el(doc, 'tbody');
    CATEGORIAS.forEach(function (c) {
      var linha = el(doc, 'tr');
      var td = el(doc, 'td');
      td.appendChild(el(doc, 'span', 'tk ' + c.css, c.rotulo));
      linha.appendChild(td);
      var ex = el(doc, 'td');
      ex.appendChild(el(doc, 'code', null, c.exemplos));
      linha.appendChild(ex);
      linha.appendChild(el(doc, 'td', null, c.descricao));
      corpo.appendChild(linha);
    });
    tabela.appendChild(corpo);
    cont.appendChild(tabela);
  }

  /* ---------- Tabela e sequência ---------- */
  function renderTabela(doc, corpo, aviso, tokens) {
    limpar(corpo);
    tokens = tokens || [];
    tokens.slice(0, LIMITE_TABELA).forEach(function (t, i) {
      var tr = el(doc, 'tr');
      tr.appendChild(el(doc, 'td', 'num', String(i + 1)));
      var tdTipo = el(doc, 'td');
      tdTipo.appendChild(el(doc, 'span', 'tk ' + categoria(t.tipo).css, t.tipo));
      tr.appendChild(tdTipo);
      var tdLex = el(doc, 'td');
      tdLex.appendChild(el(doc, 'code', null, t.lexema));
      tr.appendChild(tdLex);
      tr.appendChild(el(doc, 'td', 'num', String(t.linha)));
      tr.appendChild(el(doc, 'td', 'num', String(t.coluna)));
      corpo.appendChild(tr);
    });
    if (aviso) {
      aviso.textContent = tokens.length > LIMITE_TABELA
        ? 'Mostrando os primeiros ' + LIMITE_TABELA + ' de ' + tokens.length + ' tokens.'
        : (tokens.length === 0 ? 'Nenhum token reconhecido.' : '');
    }
  }

  function renderSequencia(doc, cont, tokens) {
    limpar(cont);
    tokens = tokens || [];
    tokens.slice(0, LIMITE_SEQUENCIA).forEach(function (t) {
      var c = categoria(t.tipo);
      var item = el(doc, 'span', 'seq-item tk ' + c.css, '<' + c.curto + ', ' + t.lexema + '>');
      item.title = c.rotulo + ' (linha ' + t.linha + ', coluna ' + t.coluna + ')';
      cont.appendChild(item);
    });
    if (tokens.length > LIMITE_SEQUENCIA) {
      cont.appendChild(el(doc, 'span', 'seq-mais', '… e mais ' + (tokens.length - LIMITE_SEQUENCIA) + ' tokens'));
    }
    if (tokens.length === 0) cont.appendChild(el(doc, 'span', 'seq-mais', 'Nenhum token.'));
  }

  /* ---------- Código colorido ---------- */
  function itensOrdenados(dados) {
    var itens = [];
    (dados.tokens || []).forEach(function (d) { itens.push({ classe: 'token', d: d }); });
    (dados.erros || []).forEach(function (d) { itens.push({ classe: 'erro', d: d }); });
    (dados.comentarios || []).forEach(function (d) { itens.push({ classe: 'comentario', d: d }); });
    itens.sort(function (a, b) { return a.d.inicio - b.d.inicio; });
    return itens;
  }

  function renderCodigoColorido(doc, pre, codigo, dados) {
    limpar(pre);
    var pos = 0;
    itensOrdenados(dados).forEach(function (it) {
      var d = it.d;
      if (d.inicio < pos || d.fim > codigo.length) return; // defesa contra dados inconsistentes
      if (d.inicio > pos) pre.appendChild(doc.createTextNode(codigo.slice(pos, d.inicio)));
      var span;
      if (it.classe === 'token') {
        span = el(doc, 'span', 'tk ' + categoria(d.tipo).css, codigo.slice(d.inicio, d.fim));
        span.title = categoria(d.tipo).rotulo + ' (linha ' + d.linha + ', coluna ' + d.coluna + ')';
      } else if (it.classe === 'comentario') {
        span = el(doc, 'span', 'tk tk-comentario', codigo.slice(d.inicio, d.fim));
        span.title = 'Comentário ignorado pelo scanner';
      } else {
        span = el(doc, 'span', 'tk tk-erro', codigo.slice(d.inicio, d.fim));
        span.title = mensagemErro(d);
      }
      pre.appendChild(span);
      pos = d.fim;
    });
    if (pos < codigo.length) pre.appendChild(doc.createTextNode(codigo.slice(pos)));
  }

  /* ---------- Passo a passo ---------- */
  function construirPassos(codigo, dados) {
    var passos = [];
    var pos = 0;
    itensOrdenados(dados).forEach(function (it) {
      var d = it.d;
      if (d.inicio < pos) return;
      if (d.inicio > pos) passos.push({ tipo: 'espaco', de: pos, ate: d.inicio, fimLido: d.inicio, final: true });
      var caminho = d.caminho || [];
      if (it.classe === 'comentario' || caminho.length === 0) {
        passos.push({ tipo: it.classe, item: d, k: 0, total: 0, fimLido: d.fim, final: true });
      } else {
        var acumulado = d.inicio;
        for (var k = 0; k < caminho.length; k++) {
          acumulado += caminho[k].c.length;
          var ultimo = k === caminho.length - 1;
          passos.push({ tipo: it.classe, item: d, k: k + 1, total: caminho.length,
            fimLido: ultimo ? d.fim : acumulado, final: ultimo });
        }
      }
      pos = d.fim;
    });
    if (pos < codigo.length) passos.push({ tipo: 'espaco', de: pos, ate: codigo.length, fimLido: codigo.length, final: true });
    return passos;
  }

  function narrar(passo, codigo) {
    if (passo.tipo === 'espaco') {
      return 'Espaços em branco e quebras de linha são lidos e descartados: não viram tokens.';
    }
    var d = passo.item;
    if (passo.tipo === 'comentario') {
      var estilo = d.tipo === 'COMENTARIO_BLOCO' ? 'de bloco' : 'de linha';
      return 'Comentário ' + estilo + ' (linha ' + d.linha + ', coluna ' + d.coluna +
        '): o scanner o reconhece e o descarta, então ele não vira token.';
    }
    if (passo.total === 0) return mensagemErro(d);
    var p = d.caminho[passo.k - 1];
    var parcial = codigo.slice(d.inicio, passo.fimLido);
    var txt = "Lendo '" + p.c + "' (classe: " + (NOMES_CLASSE[p.classe] || p.classe) + ') → estado ' +
      p.estado + '. Lexema até agora: "' + parcial + '".';
    if (passo.final) {
      if (passo.tipo === 'token') {
        var c = categoria(d.tipo);
        txt += ' O próximo caractere não continua este lexema (maior casamento), então o token é emitido: <' +
          c.curto + ', ' + d.lexema + '> (' + c.rotulo + '), linha ' + d.linha + ', coluna ' + d.coluna + '.';
        if (d.tipo === 'PALAVRA_RESERVADA') txt += ' O lexema foi encontrado na tabela de palavras reservadas.';
      } else {
        txt += ' ' + mensagemErro(d);
      }
    }
    return txt;
  }

  function criarPassoAPasso(doc, codigo, dados, opcoes) {
    opcoes = opcoes || {};
    var agendar = opcoes.agendar || function (fn, ms) { return setTimeout(fn, ms); };
    var cancelar = opcoes.cancelar || function (h) { clearTimeout(h); };
    var $ = function (id) { return doc.getElementById(id); };
    var ui = {
      codigo: $('passos-codigo'), narracao: $('passos-narracao'), transicoes: $('passos-transicoes'),
      emitidos: $('passos-emitidos'), info: $('passos-info'), velocidade: $('passo-velocidade'),
      inicio: $('passo-inicio'), tokenAnt: $('passo-token-anterior'), anterior: $('passo-anterior'),
      proximo: $('passo-proximo'), tokenProx: $('passo-token-proximo'), fim: $('passo-fim'),
      tocar: $('passo-reproduzir')
    };
    var passos = construirPassos(codigo, dados);
    var N = passos.length;
    var idx = 0;
    var tocando = false;
    var timer = null;
    var ouvintes = [];

    var emitidos = [];
    var contagem = [0];
    passos.forEach(function (p) {
      if (p.tipo === 'token' && p.final) emitidos.push(p.item);
      contagem.push(emitidos.length);
    });

    function render() {
      var p = idx > 0 ? passos[idx - 1] : null;
      var lidoAte = p ? p.fimLido : 0;
      var atualDe = p ? (p.tipo === 'espaco' ? p.de : p.item.inicio) : 0;

      limpar(ui.codigo);
      if (atualDe > 0) ui.codigo.appendChild(el(doc, 'span', 'passo-lido', codigo.slice(0, atualDe)));
      if (lidoAte > atualDe) {
        var cls = 'passo-atual tk';
        if (p.tipo === 'token') cls += ' ' + categoria(p.item.tipo).css;
        if (p.tipo === 'erro') cls += ' tk-erro';
        if (p.tipo === 'comentario') cls += ' tk-comentario';
        ui.codigo.appendChild(el(doc, 'span', cls, codigo.slice(atualDe, lidoAte)));
      }
      if (lidoAte < codigo.length) ui.codigo.appendChild(el(doc, 'span', 'passo-resto', codigo.slice(lidoAte)));

      var texto;
      if (N === 0) texto = 'Não há nada para mostrar: o código não tem tokens, erros nem comentários.';
      else if (!p) texto = 'Pronto para começar. O scanner ainda não leu nenhum caractere; clique em Próximo ou em Reproduzir.';
      else texto = narrar(p, codigo);
      if (N > 0 && idx === N) texto += ' Fim da entrada: o scanner terminou.';
      ui.narracao.textContent = texto;

      limpar(ui.transicoes);
      if (p && (p.tipo === 'token' || p.tipo === 'erro') && p.k > 0) {
        var caminho = p.item.caminho;
        var de = Math.max(0, p.k - LIMITE_TRANSICOES);
        if (de > 0) ui.transicoes.appendChild(el(doc, 'span', 'trans-mais', '…'));
        for (var j = de; j < p.k; j++) {
          var t = caminho[j];
          var chip = el(doc, 'span', 'trans' + (j === p.k - 1 ? ' trans--atual' : '') +
            (t.estado === 'ERRO' ? ' trans--erro' : ''));
          chip.appendChild(el(doc, 'b', null, t.c));
          chip.appendChild(el(doc, 'i', null, NOMES_CLASSE[t.classe] || t.classe));
          chip.appendChild(el(doc, 'span', 'trans__seta', '→'));
          chip.appendChild(el(doc, 'u', null, t.estado));
          ui.transicoes.appendChild(chip);
        }
      }

      limpar(ui.emitidos);
      var n = contagem[idx];
      ui.emitidos.appendChild(el(doc, 'p', 'emitidos__titulo', 'Tokens reconhecidos até aqui: ' + n));
      var lista = el(doc, 'div', 'chips');
      emitidos.slice(Math.max(0, n - LIMITE_EMITIDOS), n).forEach(function (t) {
        var c = categoria(t.tipo);
        lista.appendChild(el(doc, 'span', 'seq-item tk ' + c.css, '<' + c.curto + ', ' + t.lexema + '>'));
      });
      ui.emitidos.appendChild(lista);

      ui.info.textContent = 'Passo ' + idx + ' de ' + N;
      ui.inicio.disabled = idx === 0;
      ui.anterior.disabled = idx === 0;
      ui.tokenAnt.disabled = idx === 0;
      ui.proximo.disabled = idx === N;
      ui.tokenProx.disabled = idx === N;
      ui.fim.disabled = idx === N;
      ui.tocar.disabled = N === 0;
      ui.tocar.textContent = tocando ? '⏸ Pausar' : '▶ Reproduzir';
      ui.tocar.setAttribute('aria-pressed', tocando ? 'true' : 'false');
    }

    function irPara(i) { idx = Math.max(0, Math.min(N, i)); render(); }
    function proximo() { irPara(idx + 1); }
    function anterior() { irPara(idx - 1); }
    function proximoToken() {
      var j = idx + 1;
      while (j < N && !passos[j - 1].final) j++;
      irPara(Math.min(j, N));
    }
    function tokenAnterior() {
      var j = idx - 1;
      while (j > 0 && !passos[j - 1].final) j--;
      irPara(j);
    }

    function pausar() {
      tocando = false;
      if (timer !== null) { cancelar(timer); timer = null; }
      render();
    }
    function agendarProximo() {
      var ms = VELOCIDADES[ui.velocidade ? ui.velocidade.value : 'normal'] || VELOCIDADES.normal;
      timer = agendar(function () {
        timer = null;
        if (!tocando) return;
        if (idx >= N) { pausar(); return; }
        proximo();
        if (idx >= N) pausar(); else agendarProximo();
      }, ms);
    }
    function reproduzir() {
      if (N === 0) return;
      if (idx >= N) idx = 0;
      tocando = true;
      render();
      agendarProximo();
    }
    function alternar() { if (tocando) pausar(); else reproduzir(); }

    function ligar(no, tipo, fn) { no.addEventListener(tipo, fn); ouvintes.push([no, tipo, fn]); }
    ligar(ui.inicio, 'click', function () { pausar(); irPara(0); });
    ligar(ui.tokenAnt, 'click', function () { pausar(); tokenAnterior(); });
    ligar(ui.anterior, 'click', function () { pausar(); anterior(); });
    ligar(ui.proximo, 'click', function () { pausar(); proximo(); });
    ligar(ui.tokenProx, 'click', function () { pausar(); proximoToken(); });
    ligar(ui.fim, 'click', function () { pausar(); irPara(N); });
    ligar(ui.tocar, 'click', alternar);
    ligar(ui.velocidade, 'change', function () {
      if (tocando) { if (timer !== null) cancelar(timer); agendarProximo(); }
    });

    function destruir() {
      tocando = false;
      if (timer !== null) { cancelar(timer); timer = null; }
      ouvintes.forEach(function (o) { o[0].removeEventListener(o[1], o[2]); });
      ouvintes = [];
    }

    render();
    return {
      passos: passos, irPara: irPara, proximo: proximo, anterior: anterior,
      proximoToken: proximoToken, tokenAnterior: tokenAnterior, reproduzir: reproduzir, pausar: pausar,
      estaTocando: function () { return tocando; }, indice: function () { return idx; },
      total: function () { return N; }, destruir: destruir
    };
  }

  /* ---------- Orquestração ---------- */
  function mostrarAnalise(doc, codigo, dados, opcoes) {
    var $ = function (id) { return doc.getElementById(id); };
    renderResumo(doc, $('resumo-lexico'), dados);
    renderErros(doc, $('erros-lexicos'), dados.erros);
    renderCodigoColorido(doc, $('codigo-colorido'), codigo, dados);
    renderSequencia(doc, $('sequencia-tokens'), dados.tokens);
    renderTabela(doc, $('tabela-tokens-corpo'), $('tabela-aviso'), dados.tokens);
    $('bloco-lexico').hidden = false;
    $('painel-lexico').hidden = false;
    return criarPassoAPasso(doc, codigo, dados, opcoes);
  }

  function esconderAnalise(doc, controle) {
    if (controle) controle.destruir();
    var b = doc.getElementById('bloco-lexico');
    var p = doc.getElementById('painel-lexico');
    if (b) b.hidden = true;
    if (p) p.hidden = true;
  }

  return {
    CATEGORIAS: CATEGORIAS, categoria: categoria, mensagemErro: mensagemErro,
    renderResumo: renderResumo, renderErros: renderErros, renderLegenda: renderLegenda,
    renderTabela: renderTabela, renderSequencia: renderSequencia, renderCodigoColorido: renderCodigoColorido,
    construirPassos: construirPassos, narrar: narrar, criarPassoAPasso: criarPassoAPasso,
    mostrarAnalise: mostrarAnalise, esconderAnalise: esconderAnalise,
    LIMITE_TABELA: LIMITE_TABELA, VELOCIDADES: VELOCIDADES
  };
}));
