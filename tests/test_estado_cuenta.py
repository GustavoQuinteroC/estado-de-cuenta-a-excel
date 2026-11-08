import io
from datetime import date
from decimal import Decimal

import openpyxl
import pytest

from estado_cuenta import ContrasenaIncorrecta, PdfProtegido, a_csv, a_excel, analizar, procesar
from generar_pdfs import MOVIMIENTOS_OCTUBRE, banco_ejemplo, caja_ficticia


def test_banco_con_columnas_varias_paginas_y_conceptos_de_dos_renglones():
    pdf, saldo_final = banco_ejemplo(MOVIMIENTOS_OCTUBRE, 54321.10, por_pagina=7)
    r = procesar(pdf)

    assert r.periodo == (date(2026, 10, 1), date(2026, 10, 31))
    assert r.saldo_inicial == Decimal("54321.10")
    assert r.saldo_final == Decimal(f"{saldo_final:.2f}")
    assert len(r.movimientos) == len(MOVIMIENTOS_OCTUBRE)
    assert r.cuadra is True
    assert r.avisos == []

    spei = r.movimientos[2]
    assert spei.fecha == date(2026, 10, 5)
    assert spei.concepto == "SPEI RECIBIDO DE ABARROTES DON TACHO REF 7788123 CONCEPTO FACTURA 1032"
    assert spei.abono == Decimal("15600.00") and spei.cargo == 0
    assert r.movimientos[0].cargo == Decimal("12500.00")
    assert r.movimientos[-1].abono == Decimal("12.37")
    assert r.total_cargos == Decimal(f"{sum(m[2] for m in MOVIMIENTOS_OCTUBRE):.2f}")


def test_un_solo_importe_se_clasifica_por_el_saldo():
    movs = [("03/11/2026", "VENTA MOSTRADOR", 0, 1500.0), ("04/11/2026", "PAGO HARINA", 820.5, 0),
            ("05/11/2026", "VENTA MOSTRADOR", 0, 2310.0)]
    pdf, _ = caja_ficticia(movs, 1000)
    r = procesar(pdf)

    assert [(m.cargo, m.abono) for m in r.movimientos] == [
        (0, Decimal("1500.00")), (Decimal("820.50"), 0), (0, Decimal("2310.00"))]
    assert r.saldo_inicial == Decimal("1000.00")
    assert r.cuadra is True
    assert not any(m.deducido for m in r.movimientos)


def test_pdf_protegido_con_contrasena():
    pdf, _ = banco_ejemplo(MOVIMIENTOS_OCTUBRE[:3], 100.0, contrasena="XAXX010101000")
    with pytest.raises(PdfProtegido):
        procesar(pdf)
    with pytest.raises(ContrasenaIncorrecta):
        procesar(pdf, "otra")
    assert len(procesar(pdf, "XAXX010101000").movimientos) == 3


def test_cruce_de_diciembre_a_enero():
    lineas = [
        "Periodo: DEL 15/12/2026 AL 14/01/2027",
        "FECHA   CONCEPTO                 CARGOS      ABONOS       SALDO",
        "SALDO ANTERIOR                                          1,000.00",
        "28/DIC  RENTA LOCAL               500.00                  500.00",
        "03/ENE  DEPOSITO                              250.00      750.00",
    ]
    r = analizar(lineas)
    assert [m.fecha for m in r.movimientos] == [date(2026, 12, 28), date(2027, 1, 3)]


def test_sin_saldo_ni_columnas_usa_palabras_y_avisa():
    r = analizar(["Movimientos 2026", "01/03 DEPOSITO SUCURSAL 1,000.00", "02/03 PAGO TARJETA 300.00"])
    assert r.movimientos[0].abono == Decimal("1000.00") and r.movimientos[0].deducido
    assert r.movimientos[1].cargo == Decimal("300.00")
    assert "marcados" in r.avisos[0]


def test_dos_fechas_por_renglon_y_numeros_en_el_concepto():
    lineas = [
        "Periodo: DEL 01/10/2026 AL 31/10/2026",
        "OPER    LIQ     DESCRIPCION                  CARGOS     ABONOS      SALDO",
        "SALDO ANTERIOR                                                    5,000.00",
        "02/OCT  03/OCT  12 MESES SIN INTERESES       1,200.00               3,800.00",
    ]
    m = analizar(lineas).movimientos[0]
    assert m.fecha == date(2026, 10, 2)
    assert m.concepto == "12 MESES SIN INTERESES"
    assert m.cargo == Decimal("1200.00")


def test_descuadre_genera_aviso():
    lineas = [
        "FECHA  CONCEPTO   CARGOS   ABONOS    SALDO",
        "SALDO ANTERIOR                     100.00",
        "01/05/2026 PAGO     10.00            95.00",
        "SALDO FINAL                         95.00",
    ]
    r = analizar(lineas)
    assert r.cuadra is False
    assert any("no coincide" in a for a in r.avisos)


def test_excel_y_csv():
    pdf, _ = banco_ejemplo(MOVIMIENTOS_OCTUBRE, 54321.10)
    r = procesar(pdf)
    libro = openpyxl.load_workbook(io.BytesIO(a_excel(r)))
    hoja = libro["Movimientos"]
    assert [c.value for c in hoja[1]] == ["Fecha", "Concepto", "Cargo", "Abono", "Saldo", "Nota"]
    assert hoja["A2"].value.date() == date(2026, 10, 2)
    assert hoja["C2"].value == 12500.0
    assert hoja.cell(row=len(MOVIMIENTOS_OCTUBRE) + 2, column=3).value == "=SUBTOTAL(109,[Cargo])"
    assert "Resumen" in libro.sheetnames

    lineas = a_csv(r).splitlines()
    assert lineas[0] == "fecha,concepto,cargo,abono,saldo"
    assert lineas[1].startswith("2026-10-02,PAGO PROVEEDOR")


def test_errores_claros():
    with pytest.raises(ValueError, match="no es un PDF"):
        procesar(b"esto no es un pdf")
    assert analizar(["nada que ver"]).avisos[0].startswith("No se encontraron")
