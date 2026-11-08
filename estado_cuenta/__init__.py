"""Convierte el PDF de un estado de cuenta bancario de México en movimientos y en Excel.

Corre igual en Python normal y en el navegador con Pyodide: el PDF nunca sale del equipo.
"""
from .analizar import Movimiento, Resultado, analizar
from .excel import a_csv, a_excel
from .extraer import ContrasenaIncorrecta, PdfProtegido, lineas_del_pdf

__all__ = ["Movimiento", "Resultado", "analizar", "a_csv", "a_excel", "lineas_del_pdf",
           "PdfProtegido", "ContrasenaIncorrecta", "procesar"]
__version__ = "1.0.0"


def procesar(pdf: bytes, contrasena: str | None = None) -> Resultado:
    """PDF en bytes a resultado analizado."""
    return analizar(lineas_del_pdf(pdf, contrasena))
