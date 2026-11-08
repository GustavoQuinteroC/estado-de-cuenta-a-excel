"""Reconoce movimientos en el texto de un estado de cuenta, sin depender de un banco en particular.

Cómo decide si un importe es cargo o abono, en orden:
1. Por la columna: si hay un encabezado con CARGOS/RETIROS y ABONOS/DEPÓSITOS, cada importe va a la
   columna cuyo encabezado le queda más cerca.
2. Por el saldo: si el renglón trae el saldo, la diferencia contra el saldo anterior dice el signo.
3. Por las palabras del concepto (DEPÓSITO, SPEI RECIBIDO, ABONO...), con un aviso.
"""
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

MESES = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AGO": 8,
         "SEP": 9, "SET": 9, "OCT": 10, "NOV": 11, "DIC": 12,
         "JAN": 1, "APR": 4, "AUG": 8, "DEC": 12}

_MES = "|".join(MESES)
FECHA = re.compile(
    rf"^\s*(?P<dia>\d{{1,2}})(?:[/\-.](?P<mes>\d{{1,2}})|[\s/\-.]?(?P<mestxt>{_MES})[A-Z]*)(?:[/\-.](?P<anio>\d{{4}}|\d{{2}})|\s(?P<anio4>\d{{4}}))?(?![\d,.])",
    re.IGNORECASE,
)
IMPORTE = re.compile(r"(?<![\d.,/])-?\$?\s?\d{1,3}(?:,\d{3})*\.\d{2}(?![\d%])")
PERIODO = re.compile(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4}).{1,12}?(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})")
ANIO = re.compile(r"\b(20\d{2})\b")

SALDO_INICIAL = re.compile(r"SALDO\s+(ANTERIOR|INICIAL)", re.IGNORECASE)
SALDO_FINAL = re.compile(r"SALDO\s+(FINAL|ACTUAL|AL\s+CORTE|NUEVO)", re.IGNORECASE)
COL_CARGO = re.compile(r"\b(CARGOS?|RETIROS?|DEBE|D[EÉ]BITOS?)\b", re.IGNORECASE)
COL_ABONO = re.compile(r"\b(ABONOS?|DEP[OÓ]SITOS?|HABER|CR[EÉ]DITOS?)\b", re.IGNORECASE)
COL_SALDO = re.compile(r"\bSALDOS?\b", re.IGNORECASE)
PALABRAS_ABONO = re.compile(r"DEP[OÓ]SITO|ABONO|RECIBIDO|A FAVOR|INTERES(ES)? GANADO|DEVOLUCI[OÓ]N|BONIFICACI[OÓ]N|N[OÓ]MINA RECIBIDA", re.IGNORECASE)
PIE = re.compile(r"P[AÁ]GINA\s+\d+|\bHOJA\s+\d+|ESTADO DE CUENTA|^\s*FECHA\b", re.IGNORECASE)


@dataclass
class Movimiento:
    fecha: date
    concepto: str
    cargo: Decimal = Decimal("0")
    abono: Decimal = Decimal("0")
    saldo: Decimal | None = None
    deducido: bool = False  # el signo salió de las palabras del concepto, no de la columna ni del saldo

    def como_dict(self) -> dict:
        return {
            "fecha": self.fecha.isoformat(), "concepto": self.concepto,
            "cargo": float(self.cargo), "abono": float(self.abono),
            "saldo": None if self.saldo is None else float(self.saldo), "deducido": self.deducido,
        }


@dataclass
class Resultado:
    movimientos: list[Movimiento] = field(default_factory=list)
    saldo_inicial: Decimal | None = None
    saldo_final: Decimal | None = None
    periodo: tuple[date, date] | None = None
    avisos: list[str] = field(default_factory=list)

    @property
    def total_cargos(self) -> Decimal:
        return sum((m.cargo for m in self.movimientos), Decimal("0"))

    @property
    def total_abonos(self) -> Decimal:
        return sum((m.abono for m in self.movimientos), Decimal("0"))

    @property
    def cuadra(self) -> bool | None:
        """Saldo inicial + abonos - cargos = saldo final. None si el PDF no trae ambos saldos."""
        if self.saldo_inicial is None or self.saldo_final is None:
            return None
        return self.saldo_inicial + self.total_abonos - self.total_cargos == self.saldo_final

    def como_dict(self) -> dict:
        def num(valor):
            return None if valor is None else float(valor)
        return {
            "movimientos": [m.como_dict() for m in self.movimientos],
            "saldo_inicial": num(self.saldo_inicial), "saldo_final": num(self.saldo_final),
            "total_cargos": float(self.total_cargos), "total_abonos": float(self.total_abonos),
            "periodo": None if self.periodo is None else [d.isoformat() for d in self.periodo],
            "cuadra": self.cuadra, "avisos": list(self.avisos),
        }


def importe(texto: str) -> Decimal:
    limpio = texto.replace("$", "").replace(",", "").replace(" ", "")
    return Decimal(limpio)


def _importes(linea: str) -> list[tuple[Decimal, int]]:
    """Importes del renglón con la columna donde terminan (van alineados a la derecha)."""
    return [(importe(m.group()), m.end()) for m in IMPORTE.finditer(linea)]


def _encabezado(linea: str) -> dict[str, int] | None:
    cargo, abono = COL_CARGO.search(linea), COL_ABONO.search(linea)
    if not (cargo and abono):
        return None
    columnas = {"cargo": cargo.end(), "abono": abono.end()}
    saldo = COL_SALDO.search(linea)
    if saldo:
        columnas["saldo"] = saldo.end()
    return columnas


def _periodo(lineas: list[str]) -> tuple[date, date] | None:
    for linea in lineas[:40]:
        m = PERIODO.search(linea)
        if m:
            d1, m1, a1, d2, m2, a2 = map(int, m.groups())
            try:
                return date(a1, m1, d1), date(a2, m2, d2)
            except ValueError:
                continue
    return None


class _Fechas:
    """Completa el año de fechas como 05/OCT con el periodo, y cruza de diciembre a enero."""

    def __init__(self, periodo: tuple[date, date] | None, lineas: list[str]):
        self.periodo = periodo
        anios = [int(a) for linea in lineas[:40] for a in ANIO.findall(linea)]
        self.anio = periodo[1].year if periodo else (max(anios) if anios else date.today().year)

    def leer(self, linea: str) -> tuple[date, int] | None:
        m = FECHA.match(linea)
        if not m:
            return None
        dia = int(m["dia"])
        mes = int(m["mes"]) if m["mes"] else MESES[m["mestxt"][:3].upper()]
        if m["anio"] or m["anio4"]:
            anio = int(m["anio"] or m["anio4"])
            anio += 2000 if anio < 100 else 0
        else:
            anio = self.anio
            if self.periodo and self.periodo[0].year != self.periodo[1].year and mes >= self.periodo[0].month:
                anio = self.periodo[0].year
        try:
            return date(anio, mes, dia), m.end()
        except ValueError:
            return None


def analizar(lineas: list[str]) -> Resultado:
    resultado = Resultado(periodo=_periodo(lineas))
    fechas = _Fechas(resultado.periodo, lineas)
    columnas: dict[str, int] | None = None
    saldo_previo: Decimal | None = None
    ultimo: Movimiento | None = None
    deducidos = 0

    for linea in lineas:
        encabezado = _encabezado(linea)
        if encabezado and not FECHA.match(linea):
            columnas = encabezado
            ultimo = None
            continue

        montos = _importes(linea)
        if SALDO_INICIAL.search(linea) and montos:
            if resultado.saldo_inicial is None:
                resultado.saldo_inicial = montos[-1][0]
                saldo_previo = resultado.saldo_inicial
            ultimo = None
            continue
        if SALDO_FINAL.search(linea) and montos:
            resultado.saldo_final = montos[-1][0]
            ultimo = None
            continue

        leida = fechas.leer(linea)
        if leida is None:
            # Renglón sin fecha: si no trae importes y sigue a un movimiento, es parte de su concepto.
            if ultimo is not None and not montos and not PIE.search(linea) and len(linea.strip()) <= 120:
                ultimo.concepto = f"{ultimo.concepto} {' '.join(linea.split())}"
            else:
                ultimo = None
            continue
        if not montos:
            ultimo = None
            continue

        fecha, fin_fecha = leida
        primero = IMPORTE.search(linea, fin_fecha)
        fin_concepto = primero.start() if primero else len(linea)
        concepto_crudo = linea[fin_fecha:fin_concepto]
        # Algunos bancos imprimen dos fechas (operación y liquidación): se usa la primera.
        segunda = fechas.leer(concepto_crudo)
        if segunda:
            concepto_crudo = concepto_crudo[segunda[1]:]
        concepto = " ".join(concepto_crudo.split())

        mov = Movimiento(fecha=fecha, concepto=concepto)
        sin_asignar: list[Decimal] = []
        if columnas:
            for valor, fin in montos:
                destino = min(columnas, key=lambda c: abs(columnas[c] - fin))
                if destino == "saldo":
                    mov.saldo = valor
                elif destino == "cargo":
                    mov.cargo += abs(valor)
                else:
                    mov.abono += abs(valor)
        else:
            if len(montos) >= 2:
                mov.saldo = montos[-1][0]
                sin_asignar = [v for v, _ in montos[:-1]]
            else:
                sin_asignar = [montos[0][0]]

        for valor in sin_asignar:
            if valor < 0:
                mov.cargo += -valor
            elif saldo_previo is not None and mov.saldo is not None and saldo_previo - valor == mov.saldo:
                mov.cargo += valor
            elif saldo_previo is not None and mov.saldo is not None and saldo_previo + valor == mov.saldo:
                mov.abono += valor
            else:
                mov.deducido = True
                deducidos += 1
                if PALABRAS_ABONO.search(concepto):
                    mov.abono += valor
                else:
                    mov.cargo += valor

        if mov.saldo is not None:
            saldo_previo = mov.saldo
        elif saldo_previo is not None:
            saldo_previo = saldo_previo - mov.cargo + mov.abono
        resultado.movimientos.append(mov)
        ultimo = mov

    _revisar(resultado, deducidos)
    return resultado


def _revisar(resultado: Resultado, deducidos: int) -> None:
    if not resultado.movimientos:
        resultado.avisos.append("No se encontraron movimientos. Puede ser un formato que aún no se reconoce.")
        return

    saldo = resultado.saldo_inicial
    descuadres = 0
    for mov in resultado.movimientos:
        if saldo is not None and mov.saldo is not None and saldo - mov.cargo + mov.abono != mov.saldo:
            descuadres += 1
        if mov.saldo is not None:
            saldo = mov.saldo
        elif saldo is not None:
            saldo = saldo - mov.cargo + mov.abono

    if deducidos:
        resultado.avisos.append(f"{deducidos} movimiento(s) se clasificaron por las palabras del concepto. Revísalos: están marcados.")
    if descuadres:
        resultado.avisos.append(f"En {descuadres} renglón(es) el saldo impreso no coincide con la suma. Compara contra el PDF.")
    if resultado.cuadra is False:
        diferencia = resultado.saldo_inicial + resultado.total_abonos - resultado.total_cargos - resultado.saldo_final
        resultado.avisos.append(f"Los totales no cuadran con el saldo final por ${diferencia:,.2f}. Puede faltar algún movimiento.")
