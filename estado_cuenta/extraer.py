"""Texto del PDF conservando las columnas, una línea por renglón impreso."""
import io

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError


class PdfProtegido(Exception):
    """El PDF pide contraseña y no se dio ninguna."""


class ContrasenaIncorrecta(Exception):
    """La contraseña no abre el PDF."""


def lineas_del_pdf(pdf: bytes, contrasena: str | None = None) -> list[str]:
    try:
        lector = PdfReader(io.BytesIO(pdf))
    except PdfReadError as error:
        raise ValueError("El archivo no es un PDF válido o está dañado.") from error

    if lector.is_encrypted:
        if not contrasena:
            raise PdfProtegido("El PDF está protegido. Escribe su contraseña; muchos bancos usan tu RFC o tu fecha de nacimiento.")
        if not lector.decrypt(contrasena):
            raise ContrasenaIncorrecta("La contraseña no abre el PDF. Revisa mayúsculas y que no tenga espacios.")

    lineas: list[str] = []
    try:
        for pagina in lector.pages:
            texto = pagina.extract_text(extraction_mode="layout") or ""
            lineas.extend(linea.rstrip() for linea in texto.splitlines() if linea.strip())
    except FileNotDecryptedError as error:
        raise ContrasenaIncorrecta("La contraseña no abre el PDF.") from error

    if not lineas:
        raise ValueError("El PDF no tiene texto: parece escaneado como imagen. Pide al banco el estado de cuenta digital.")
    return lineas
