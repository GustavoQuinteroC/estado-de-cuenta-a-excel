"""Estados de cuenta FICTICIOS para las pruebas: bancos, personas y movimientos inventados."""
from fpdf import FPDF
from fpdf.enums import EncryptionMethod


def _monto(valor):
    return f"{valor:,.2f}" if valor else ""


def banco_ejemplo(movimientos, saldo_inicial, periodo=("01/10/2026", "31/10/2026"), contrasena=None, por_pagina=18):
    """Formato con columnas CARGOS / ABONOS / SALDO y fechas tipo 05/OCT."""
    pdf = FPDF(format="letter")
    if contrasena:
        pdf.set_encryption(owner_password="duenio-ficticio", user_password=contrasena, encryption_method=EncryptionMethod.AES_128)
    pdf.set_font("Helvetica", size=9)

    def encabezado():
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "BANCO EJEMPLO S.A. - ESTADO DE CUENTA", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=9)
        pdf.cell(0, 5, "Cliente: Refrescos Polar S.A. de C.V.   Cuenta: 0123456789", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 5, f"Periodo: DEL {periodo[0]} AL {periodo[1]}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 9)
        for texto, ancho, alin in (("FECHA", 18, "L"), ("DESCRIPCION", 92, "L"), ("CARGOS", 28, "R"), ("ABONOS", 28, "R"), ("SALDO", 28, "R")):
            pdf.cell(ancho, 6, texto, align=alin)
        pdf.ln(6)
        pdf.set_font("Helvetica", size=9)

    encabezado()
    pdf.cell(110, 5, "SALDO ANTERIOR")
    pdf.cell(84, 5, _monto(saldo_inicial), align="R", new_x="LMARGIN", new_y="NEXT")
    saldo = saldo_inicial
    for i, (fecha, concepto, cargo, abono) in enumerate(movimientos):
        if i and i % por_pagina == 0:
            pdf.cell(0, 5, f"Pagina {i // por_pagina} de varias", align="C", new_x="LMARGIN", new_y="NEXT")
            encabezado()
        saldo = round(saldo - cargo + abono, 2)
        lineas = concepto.split("\n")
        pdf.cell(18, 5, fecha)
        pdf.cell(92, 5, lineas[0])
        pdf.cell(28, 5, _monto(cargo), align="R")
        pdf.cell(28, 5, _monto(abono), align="R")
        pdf.cell(28, 5, _monto(saldo), align="R", new_x="LMARGIN", new_y="NEXT")
        for extra in lineas[1:]:
            pdf.cell(18, 5, "")
            pdf.cell(92, 5, extra, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.cell(110, 5, "SALDO FINAL")
    pdf.cell(84, 5, _monto(saldo), align="R", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output()), saldo


def caja_ficticia(movimientos, saldo_inicial):
    """Formato con fecha completa, un solo importe con signo implícito y saldo; sin columnas separadas."""
    pdf = FPDF(format="letter")
    pdf.add_page()
    pdf.set_font("Courier", size=9)
    pdf.cell(0, 6, "CAJA POPULAR FICTICIA - MOVIMIENTOS DE LA CUENTA", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Socio: Panaderia La Espiga   Periodo: noviembre 2026", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Saldo inicial: ${saldo_inicial:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Fecha       Concepto                                   Importe        Saldo", new_x="LMARGIN", new_y="NEXT")
    saldo = saldo_inicial
    for fecha, concepto, cargo, abono in movimientos:
        saldo = round(saldo - cargo + abono, 2)
        importe = abono or cargo
        pdf.cell(0, 6, f"{fecha:<12}{concepto:<40}{importe:>12,.2f}{saldo:>14,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Saldo final: ${saldo:,.2f}", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output()), saldo


MOVIMIENTOS_OCTUBRE = [
    ("02/OCT", "PAGO PROVEEDOR DISTRIBUIDORA NORTE", 12500.00, 0),
    ("03/OCT", "DEPOSITO EN EFECTIVO SUC 0457", 0, 8300.50),
    ("05/OCT", "SPEI RECIBIDO DE ABARROTES DON TACHO\nREF 7788123 CONCEPTO FACTURA 1032", 0, 15600.00),
    ("07/OCT", "COMISION POR MANEJO DE CUENTA", 250.00, 0),
    ("07/OCT", "IVA COMISION", 40.00, 0),
    ("10/OCT", "PAGO DE NOMINA QUINCENA 19", 21430.75, 0),
    ("15/OCT", "TRASPASO A FAVOR CTA 9988", 0, 30000.00),
    ("18/OCT", "CARGO DOMICILIADO LUZ", 1873.20, 0),
    ("21/OCT", "COMPRA TARJETA PAPELERIA LA ESTRELLA", 389.90, 0),
    ("25/OCT", "PAGO DE NOMINA QUINCENA 20", 21430.75, 0),
    ("28/OCT", "DEPOSITO CHEQUE 0012", 0, 4200.00),
    ("31/OCT", "INTERESES GANADOS", 0, 12.37),
]
