const $ = (id) => document.getElementById(id);
const trabajador = new Worker('js/trabajador.js', { type: 'module' });
const dinero = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' });
const fechaCorta = new Intl.DateTimeFormat('es-MX', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' });
let pdfActual = null;
let nombreBase = 'estado-de-cuenta';
let enlaces = [];

const estado = (texto, tipo = '') => {
  $('estado').textContent = texto;
  $('estado').dataset.tipo = tipo;
};
const fecha = (iso) => fechaCorta.format(new Date(`${iso}T00:00:00Z`));
const monto = (n) => (n ? dinero.format(n) : '');

// Python se prepara en cuanto abre la página, mientras eliges el archivo.
trabajador.postMessage({ tipo: 'preparar' });
estado('Preparando Python en tu navegador (solo la primera vez tarda unos segundos)…');

trabajador.onmessage = ({ data }) => {
  if (data.tipo === 'progreso') estado(data.texto);
  if (data.tipo === 'preparado') estado(pdfActual ? '' : 'Listo. Elige el PDF de tu estado de cuenta.', 'listo');
  if (data.tipo === 'error') mostrarError(data);
  if (data.tipo === 'resultado') mostrar(data);
  $('convertir').disabled = false;
};

function mostrarError({ error, mensaje }) {
  estado(mensaje, 'error');
  $('campo-contrasena').hidden = !(error === 'protegido' || error === 'contrasena');
  if (!$('campo-contrasena').hidden) $('contrasena').focus();
}

async function convertir() {
  if (!pdfActual) return;
  $('convertir').disabled = true;
  $('resultado').hidden = true;
  estado('Leyendo el PDF…');
  trabajador.postMessage({ tipo: 'procesar', pdf: pdfActual.slice(0), contrasena: $('contrasena').value });
}

async function elegir(archivo) {
  if (!archivo) return;
  if (archivo.type && archivo.type !== 'application/pdf') {
    estado('Ese archivo no es un PDF.', 'error');
    return;
  }
  pdfActual = await archivo.arrayBuffer();
  nombreBase = archivo.name.replace(/\.pdf$/i, '') || 'estado-de-cuenta';
  $('nombre-archivo').textContent = archivo.name;
  $('contrasena').value = '';
  $('campo-contrasena').hidden = true;
  convertir();
}

function descarga(id, contenido, tipo, nombre) {
  const url = URL.createObjectURL(new Blob([contenido], { type: tipo }));
  enlaces.push(url);
  Object.assign($(id), { href: url, download: nombre });
}

function mostrar({ resultado: r, excel, csv }) {
  enlaces.forEach(URL.revokeObjectURL);
  enlaces = [];
  descarga('descargar-excel', excel, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', `${nombreBase}.xlsx`);
  descarga('descargar-csv', `﻿${csv}`, 'text/csv;charset=utf-8', `${nombreBase}.csv`);

  const cifras = [
    ['Movimientos', r.movimientos.length.toLocaleString('es-MX')],
    ['Saldo inicial', r.saldo_inicial === null ? 'Sin dato' : dinero.format(r.saldo_inicial)],
    ['Abonos', dinero.format(r.total_abonos)],
    ['Cargos', dinero.format(r.total_cargos)],
    ['Saldo final', r.saldo_final === null ? 'Sin dato' : dinero.format(r.saldo_final)],
  ];
  $('cifras').replaceChildren(...cifras.map(([etiqueta, valor]) => {
    const div = document.createElement('div');
    div.append(Object.assign(document.createElement('dt'), { textContent: etiqueta }), Object.assign(document.createElement('dd'), { textContent: valor }));
    return div;
  }));

  const sello = $('cuadre');
  sello.dataset.cuadra = String(r.cuadra);
  sello.textContent = r.cuadra === true ? 'Cuadra: saldo inicial + abonos − cargos = saldo final'
    : r.cuadra === false ? 'No cuadra con el saldo final: revisa los avisos'
    : 'El PDF no trae saldo inicial y final para comprobar';
  $('periodo').textContent = r.periodo ? `Periodo del ${fecha(r.periodo[0])} al ${fecha(r.periodo[1])}` : '';
  $('avisos').replaceChildren(...r.avisos.map((a) => Object.assign(document.createElement('li'), { textContent: a })));

  $('filas').replaceChildren(...r.movimientos.map((m) => {
    const tr = document.createElement('tr');
    if (m.deducido) {
      tr.className = 'revisar';
      tr.title = 'Clasificado por las palabras del concepto: revísalo';
    }
    for (const [texto, clase] of [[fecha(m.fecha), ''], [m.concepto, 'concepto'], [monto(m.cargo), 'num'], [monto(m.abono), 'num'], [m.saldo === null ? '' : dinero.format(m.saldo), 'num']]) {
      tr.append(Object.assign(document.createElement('td'), { textContent: texto, className: clase }));
    }
    return tr;
  }));
  $('resultado').hidden = false;
  estado(`${r.movimientos.length} movimientos listos para descargar.`, 'listo');
  $('resultado').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
}

$('archivo').addEventListener('change', (e) => elegir(e.target.files[0]));
$('convertir').addEventListener('click', convertir);
$('contrasena').addEventListener('keydown', (e) => { if (e.key === 'Enter') convertir(); });
$('ejemplo').addEventListener('click', async () => {
  const respuesta = await fetch('ejemplo.pdf');
  const blob = await respuesta.blob();
  elegir(new File([blob], 'ejemplo-banco-ficticio.pdf', { type: 'application/pdf' }));
});

const zona = $('zona');
['dragenter', 'dragover'].forEach((t) => zona.addEventListener(t, (e) => { e.preventDefault(); zona.dataset.encima = 'si'; }));
['dragleave', 'drop'].forEach((t) => zona.addEventListener(t, (e) => { e.preventDefault(); delete zona.dataset.encima; }));
zona.addEventListener('drop', (e) => elegir(e.dataTransfer.files[0]));
