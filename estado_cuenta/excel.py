"""Excel con una hoja de movimientos (tabla con filtros y totales) y otra de resumen."""
import csv
import io
from datetime import datetime

import xlsxwriter

from .analizar import Resultado


def a_excel(resultado: Resultado, titulo: str = "Estado de cuenta") -> bytes:
    salida = io.BytesIO()
    libro = xlsxwriter.Workbook(salida, {"in_memory": True})
    libro.set_properties({"title": titulo, "author": "estado-de-cuenta-a-excel", "created": datetime(2000, 1, 1)})
    fecha = libro.add_format({"num_format": "dd/mm/yyyy"})
    dinero = libro.add_format({"num_format": "$#,##0.00;-$#,##0.00;\"\""})
    dinero_resumen = libro.add_format({"num_format": "$#,##0.00;-$#,##0.00"})
    marcado = libro.add_format({"bg_color": "#FDECD3"})
    negrita = libro.add_format({"bold": True})
    titulo_fmt = libro.add_format({"bold": True, "font_size": 14})

    hoja = libro.add_worksheet("Movimientos")
    filas = [[m.fecha, m.concepto, float(m.cargo) or None, float(m.abono) or None,
              None if m.saldo is None else float(m.saldo), "Revisar" if m.deducido else ""]
             for m in resultado.movimientos]
    ultima = max(len(filas), 1)
    hoja.add_table(0, 0, ultima + 1, 5, {
        "name": "Movimientos",
        "style": "Table Style Medium 2",
        "total_row": True,
        "data": filas or None,
        "columns": [
            {"header": "Fecha", "format": fecha, "total_string": "Totales"},
            {"header": "Concepto"},
            {"header": "Cargo", "format": dinero, "total_function": "sum"},
            {"header": "Abono", "format": dinero, "total_function": "sum"},
            {"header": "Saldo", "format": dinero},
            {"header": "Nota"},
        ],
    })
    hoja.set_column(0, 0, 12)
    hoja.set_column(1, 1, 60)
    hoja.set_column(2, 4, 15)
    hoja.set_column(5, 5, 10)
    hoja.freeze_panes(1, 0)
    if filas:
        hoja.conditional_format(1, 0, len(filas), 5, {"type": "formula", "criteria": '=$F2="Revisar"', "format": marcado})

    resumen = libro.add_worksheet("Resumen")
    resumen.set_column(0, 0, 34)
    resumen.set_column(1, 1, 18)
    resumen.write(0, 0, titulo, titulo_fmt)
    fila = 2
    if resultado.periodo:
        resumen.write(fila, 0, "Periodo")
        resumen.write(fila, 1, f"{resultado.periodo[0]:%d/%m/%Y} al {resultado.periodo[1]:%d/%m/%Y}")
        fila += 1
    datos = [
        ("Saldo inicial", resultado.saldo_inicial),
        ("Total de abonos", "=SUBTOTAL(109,Movimientos[Abono])"),
        ("Total de cargos", "=SUBTOTAL(109,Movimientos[Cargo])"),
        ("Saldo final según el PDF", resultado.saldo_final),
    ]
    inicio = fila
    for etiqueta, valor in datos:
        resumen.write(fila, 0, etiqueta)
        if isinstance(valor, str):
            resumen.write_formula(fila, 1, valor, dinero_resumen)
        elif valor is not None:
            resumen.write_number(fila, 1, float(valor), dinero_resumen)
        fila += 1
    resumen.write(fila, 0, "Saldo calculado", negrita)
    if resultado.saldo_inicial is not None:
        resumen.write_formula(fila, 1, f"=B{inicio + 1}+B{inicio + 2}-B{inicio + 3}", dinero_resumen)
    fila += 1
    resumen.write(fila, 0, "Movimientos")
    resumen.write_number(fila, 1, len(resultado.movimientos))
    fila += 2
    for aviso in resultado.avisos:
        resumen.write(fila, 0, aviso)
        fila += 1
    resumen.write(fila + 1, 0, "Generado en tu navegador: el PDF no se envió a ningún servidor.")

    libro.close()
    return salida.getvalue()


def a_csv(resultado: Resultado) -> str:
    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(["fecha", "concepto", "cargo", "abono", "saldo"])
    for m in resultado.movimientos:
        escritor.writerow([m.fecha.isoformat(), m.concepto, f"{m.cargo:.2f}", f"{m.abono:.2f}", "" if m.saldo is None else f"{m.saldo:.2f}"])
    return salida.getvalue()
