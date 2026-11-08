// Corre Python (Pyodide) fuera del hilo de la página. El PDF llega como ArrayBuffer y nunca se envía a la red.
const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/';
const base = new URL('../', self.location.href);

let listo = null;

async function preparar() {
  const { loadPyodide } = await import(`${PYODIDE}pyodide.mjs`);
  avisar('Descargando Python…');
  const py = await loadPyodide({ indexURL: PYODIDE });
  avisar('Instalando lectores de PDF y de Excel…');
  await py.loadPackage(['micropip', 'cryptography']);
  const ruedas = await (await fetch(new URL('wheels/lista.json', base))).json();
  const micropip = py.pyimport('micropip');
  await micropip.install.callKwargs(py.toPy(ruedas.map((r) => new URL(`wheels/${r}`, base).href)), { deps: false });

  const archivos = await (await fetch(new URL('py/lista.json', base))).json();
  py.FS.mkdirTree('/app/estado_cuenta');
  for (const nombre of archivos) {
    const codigo = await (await fetch(new URL(`py/estado_cuenta/${nombre}`, base))).text();
    py.FS.writeFile(`/app/estado_cuenta/${nombre}`, codigo);
  }
  py.runPython(`
import sys, json
sys.path.insert(0, '/app')
import estado_cuenta

def convertir(pdf, contrasena):
    datos = bytes(pdf.to_py() if hasattr(pdf, 'to_py') else pdf)
    try:
        r = estado_cuenta.procesar(datos, contrasena or None)
    except estado_cuenta.PdfProtegido as e:
        return json.dumps({'error': 'protegido', 'mensaje': str(e)}), None, None
    except estado_cuenta.ContrasenaIncorrecta as e:
        return json.dumps({'error': 'contrasena', 'mensaje': str(e)}), None, None
    except ValueError as e:
        return json.dumps({'error': 'formato', 'mensaje': str(e)}), None, None
    return json.dumps(r.como_dict()), estado_cuenta.a_excel(r), estado_cuenta.a_csv(r)
`);
  return py;
}

function avisar(texto) {
  self.postMessage({ tipo: 'progreso', texto });
}

self.onmessage = async ({ data }) => {
  try {
    listo ??= preparar();
    const py = await listo;
    if (data.tipo === 'preparar') {
      self.postMessage({ tipo: 'preparado' });
      return;
    }
    avisar('Leyendo el PDF…');
    const convertir = py.globals.get('convertir');
    const salida = convertir(new Uint8Array(data.pdf), data.contrasena ?? '');
    const [json, excel, csv] = salida.toJs();
    salida.destroy();
    const resultado = JSON.parse(json);
    if (resultado.error) {
      self.postMessage({ tipo: 'error', ...resultado });
      return;
    }
    const xlsx = excel.slice().buffer;
    self.postMessage({ tipo: 'resultado', resultado, excel: xlsx, csv }, [xlsx]);
  } catch (error) {
    listo = null;
    self.postMessage({ tipo: 'error', error: 'interno', mensaje: `No se pudo cargar Python o leer el archivo: ${error.message}` });
  }
};
