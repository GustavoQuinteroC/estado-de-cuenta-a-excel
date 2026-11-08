"""Arma dist/: la página, el paquete de Python, las ruedas que instala Pyodide y un PDF de ejemplo ficticio."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIST = RAIZ / "dist"


def main() -> None:
    shutil.rmtree(DIST, ignore_errors=True)
    shutil.copytree(RAIZ / "web", DIST)

    paquete = DIST / "py" / "estado_cuenta"
    paquete.mkdir(parents=True)
    archivos = sorted(p.name for p in (RAIZ / "estado_cuenta").glob("*.py"))
    for nombre in archivos:
        shutil.copy(RAIZ / "estado_cuenta" / nombre, paquete / nombre)
    (DIST / "py" / "lista.json").write_text(json.dumps(archivos))

    ruedas = DIST / "wheels"
    subprocess.run([sys.executable, "-m", "pip", "download", "-q", "--no-deps", "--only-binary", ":all:",
                    "-r", str(RAIZ / "requirements.txt"), "-d", str(ruedas)], check=True)
    (ruedas / "lista.json").write_text(json.dumps(sorted(p.name for p in ruedas.glob("*.whl"))))

    sys.path.insert(0, str(RAIZ / "tests"))
    from generar_pdfs import MOVIMIENTOS_OCTUBRE, banco_ejemplo
    pdf, _ = banco_ejemplo(MOVIMIENTOS_OCTUBRE, 54321.10, por_pagina=8)
    (DIST / "ejemplo.pdf").write_bytes(pdf)
    print(f"dist/ listo: {len(archivos)} módulos, {len(list(ruedas.glob('*.whl')))} ruedas")


if __name__ == "__main__":
    main()
