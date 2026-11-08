# Estado de cuenta a Excel

Convierte el PDF del estado de cuenta de tu banco en un Excel con fecha, concepto, cargo, abono y saldo de cada movimiento. Comprueba que los totales cuadren con el saldo final.

**Pruébalo:** https://proyectos.gustavoquintero.dev/estado-de-cuenta/ (trae un estado de cuenta de ejemplo de un banco ficticio).

## El PDF no sale de tu equipo

La página carga Python dentro del navegador con [Pyodide](https://pyodide.org) y lo corre en un Web Worker. El PDF se lee en tu computadora y el Excel se arma ahí mismo. Cuando Python termina de cargar puedes desconectarte de internet y sigue funcionando. La prueba en navegador verifica que la página no envíe ninguna petición POST.

## Qué reconoce

- PDF digitales con columnas de **cargos y abonos** (o retiros y depósitos), o con **un importe y el saldo**.
- Fechas como `05/OCT`, `05-10-2026`, `5 OCT 2026` o dos fechas por renglón (operación y liquidación). El año sale del periodo del estado de cuenta, incluso cuando cruza de diciembre a enero.
- Conceptos de varios renglones y encabezados que se repiten en cada página.
- PDF protegidos con contraseña.

No funciona con PDF escaneados como imagen.

### Cómo decide si es cargo o abono

1. **Por la columna:** cada importe va a la columna cuyo encabezado le queda más cerca.
2. **Por el saldo:** si el banco usa una sola columna, la diferencia contra el saldo anterior dice el signo.
3. **Por las palabras del concepto** (DEPÓSITO, SPEI RECIBIDO, A FAVOR…) solo si no hay nada más, y marca el renglón para revisarlo.

Al final suma: saldo inicial + abonos − cargos debe dar el saldo final. Si no, avisa la diferencia y los renglones donde el saldo impreso no coincide.

## Usarlo desde Python

```python
from estado_cuenta import procesar, a_excel

resultado = procesar(open("octubre.pdf", "rb").read(), contrasena="XAXX010101000")
print(resultado.cuadra, len(resultado.movimientos))
open("octubre.xlsx", "wb").write(a_excel(resultado))
```

El Excel trae una tabla con filtros y totales que se recalculan al filtrar, fechas y montos como números, y una hoja de resumen.

## Desarrollo

```bash
pip install -r requirements-dev.txt
pytest                          # analizador, Excel y PDF protegidos
python herramientas/construir.py  # arma dist/ con la página, el paquete y las ruedas para Pyodide
npm ci && npm run e2e           # Playwright con Pyodide real
```

Las pruebas generan estados de cuenta **ficticios** con fpdf2: bancos, clientes y movimientos inventados.

## Licencia

MIT. Hecho por [Gustavo Quintero](https://gustavoquintero.dev).
