"""
epw_io.py — Lectura y escritura de archivos EnergyPlus Weather (EPW).

Preserva la cabecera textual y permite modificar el cuerpo de datos horario
(8760 o 8784 filas). Índices de campo según especificación EnergyPlus (0-based).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Optional, TextIO, Union

import pandas as pd

# Campos de datos EPW (0-based) — EnergyPlus Auxiliary Programs
EPW_YEAR = 0
EPW_MONTH = 1
EPW_DAY = 2
EPW_HOUR = 3
EPW_MINUTE = 4
EPW_DATA_SOURCE = 5
EPW_DRY_BULB = 6
EPW_DEW_POINT = 7
EPW_RH = 8
EPW_PRESSURE = 9
EPW_ET_HORIZ = 10
EPW_ET_DIRECT = 11
EPW_IR_HORIZ = 12
EPW_GHI = 13
EPW_DNI = 14
EPW_DHI = 15
EPW_GLO_ILLUM = 16
EPW_DIR_ILLUM = 17
EPW_DIF_ILLUM = 18
EPW_ZENITH_LUM = 19
EPW_WIND_DIR = 20
EPW_WIND_SPEED = 21
EPW_TOTAL_SKY = 22
EPW_OPAQUE_SKY = 23
EPW_VISIBILITY = 24
EPW_CEILING = 25
EPW_PRESENT_WX = 26
EPW_PRECIP_WTR = 27
EPW_AEROSOL = 28
EPW_SNOW_DEPTH = 29
EPW_DAYS_SINCE_SNOW = 30
EPW_ALBEDO = 31
EPW_LIQUID_PRECIP_DEPTH = 32
EPW_LIQUID_PRECIP_RATE = 33

EPW_N_FIELDS = 35

HEADER_PREFIXES = (
    "LOCATION",
    "DESIGN CONDITIONS",
    "TYPICAL/EXTREME PERIODS",
    "GROUND TEMPERATURES",
    "HOLIDAYS/DAYLIGHT SAVINGS",
    "COMMENTS 1",
    "COMMENTS 2",
    "DATA PERIODS",
)

PathLike = Union[str, Path]
FileLike = Union[PathLike, TextIO, BinaryIO]


@dataclass
class EpwFile:
    """Representación en memoria de un EPW."""

    header_lines: list[str]
    data: pd.DataFrame  # columnas: field_0 … field_N-1 (strings o numéricos)
    location: dict = field(default_factory=dict)
    n_fields: int = EPW_N_FIELDS

    @property
    def n_hours(self) -> int:
        return len(self.data)


def _as_text_lines(source: FileLike) -> list[str]:
    if hasattr(source, "read"):
        raw = source.read()
        if isinstance(raw, bytes):
            text = raw.decode("utf-8", errors="replace")
        else:
            text = raw
        return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    path = Path(source)
    text = path.read_text(encoding="utf-8", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _parse_location(line: str) -> dict:
    """Parsea la línea LOCATION del EPW."""
    parts = [p.strip() for p in line.split(",")]
    # LOCATION, City, State, Country, Source, WMO, Lat, Lon, TZ, Elevation
    out = {"raw": line}
    if len(parts) >= 10:
        try:
            out.update({
                "city": parts[1],
                "state": parts[2],
                "country": parts[3],
                "source": parts[4],
                "wmo": parts[5],
                "latitude": float(parts[6]),
                "longitude": float(parts[7]),
                "tz": float(parts[8]),
                "elevation_m": float(parts[9]),
            })
        except ValueError:
            pass
    return out


def set_location_timezone(epw: EpwFile, tz_hr: float) -> EpwFile:
    """
    Actualiza el campo de zona horaria en la línea LOCATION (índice 8).
    Conserva el resto de la cabecera. Útil cuando el EPW histórico dice -4
    pero las mediciones están en UTC-3 (Argentina actual).
    """
    new_headers = list(epw.header_lines)
    for i, line in enumerate(new_headers):
        if line.upper().startswith("LOCATION"):
            parts = line.split(",")
            if len(parts) >= 9:
                parts[8] = str(tz_hr)
                new_headers[i] = ",".join(parts)
                loc = _parse_location(new_headers[i])
                return EpwFile(
                    header_lines=new_headers,
                    data=epw.data,
                    location=loc,
                    n_fields=epw.n_fields,
                )
            break
    return epw


def stamp_generation_comments(
    epw: EpwFile,
    comments1: str,
    comments2: str,
) -> EpwFile:
    """
    Escribe/actualiza COMMENTS 1 y COMMENTS 2 en la cabecera del EPW.
    `comments1`/`comments2` deben ser líneas completas ("COMMENTS 1,...").
    """
    new_headers = list(epw.header_lines)
    found1 = found2 = False
    for i, line in enumerate(new_headers):
        upper = line.upper()
        if upper.startswith("COMMENTS 1"):
            new_headers[i] = comments1
            found1 = True
        elif upper.startswith("COMMENTS 2"):
            new_headers[i] = comments2
            found2 = True

    # Insertar antes de DATA PERIODS si faltaban
    if not found1 or not found2:
        insert_at = len(new_headers)
        for i, line in enumerate(new_headers):
            if line.upper().startswith("DATA PERIODS"):
                insert_at = i
                break
        extras = []
        if not found1:
            extras.append(comments1)
        if not found2:
            extras.append(comments2)
        new_headers[insert_at:insert_at] = extras

    return EpwFile(
        header_lines=new_headers,
        data=epw.data,
        location=dict(epw.location),
        n_fields=epw.n_fields,
    )


def read_epw(source: FileLike) -> EpwFile:
    """
    Lee un EPW desde ruta o file-like.

    Conserva líneas de cabecera exactas (sin el newline final vacío extra).
    El cuerpo se parsea como filas CSV de al menos EPW_N_FIELDS campos.
    """
    lines = _as_text_lines(source)
    # Quitar último vacío si el archivo termina en newline
    while lines and lines[-1] == "":
        lines.pop()

    header_lines: list[str] = []
    data_start = 0
    location: dict = {}

    for i, line in enumerate(lines):
        upper = line.upper()
        is_header = any(upper.startswith(p) for p in HEADER_PREFIXES)
        if is_header:
            header_lines.append(line)
            if upper.startswith("LOCATION"):
                location = _parse_location(line)
            data_start = i + 1
        else:
            # Primera línea no-header = inicio de datos
            if header_lines:
                data_start = i
                break
            # EPW malformado sin headers reconocidos: tratar todo como datos
            data_start = 0
            break

    data_rows: list[list[str]] = []
    n_fields = EPW_N_FIELDS
    for line in lines[data_start:]:
        if not line.strip():
            continue
        parts = line.split(",")
        if len(parts) < 6:
            continue
        n_fields = max(n_fields, len(parts))
        data_rows.append(parts)

    if not data_rows:
        raise ValueError("El EPW no contiene filas de datos horarios.")

    # Normalizar ancho
    for row in data_rows:
        if len(row) < n_fields:
            row.extend([""] * (n_fields - len(row)))
        elif len(row) > n_fields:
            del row[n_fields:]

    cols = [f"field_{i}" for i in range(n_fields)]
    # object evita ArrowStringArray (pandas 2.2+/3) que rechaza floats en setitem
    df = pd.DataFrame(data_rows, columns=cols, dtype=object)

    # Tipar campos temporales como int cuando sea posible
    for idx in (EPW_YEAR, EPW_MONTH, EPW_DAY, EPW_HOUR, EPW_MINUTE):
        if idx < n_fields:
            df[f"field_{idx}"] = pd.to_numeric(df[f"field_{idx}"], errors="coerce")

    return EpwFile(
        header_lines=header_lines,
        data=df,
        location=location,
        n_fields=n_fields,
    )


def write_epw(epw: EpwFile, dest: Optional[FileLike] = None) -> str:
    """
    Serializa un EpwFile a texto EPW.

    Si dest es una ruta o file-like escribible, también lo escribe.
    Retorna el string completo.
    """
    lines: list[str] = list(epw.header_lines)
    for _, row in epw.data.iterrows():
        parts = []
        for i in range(epw.n_fields):
            val = row[f"field_{i}"]
            if pd.isna(val):
                parts.append("")
            elif isinstance(val, float) and val == int(val) and i <= EPW_MINUTE:
                parts.append(str(int(val)))
            elif isinstance(val, (int, float)) and i <= EPW_MINUTE:
                parts.append(str(int(val)))
            else:
                # Radiación y meteo: EnergyPlus acepta enteros o decimales
                if isinstance(val, float):
                    # Evitar notación científica; trim .0 innecesarios
                    if abs(val - round(val)) < 1e-9:
                        parts.append(str(int(round(val))))
                    else:
                        parts.append(f"{val:.6g}")
                else:
                    parts.append(str(val))
        lines.append(",".join(parts))

    text = "\n".join(lines) + "\n"
    if dest is not None:
        if hasattr(dest, "write"):
            payload = text if not isinstance(getattr(dest, "mode", "w"), str) else text
            try:
                dest.write(text)
            except TypeError:
                dest.write(text.encode("utf-8"))
        else:
            Path(dest).write_text(text, encoding="utf-8", newline="\n")
    return text


def make_minimal_epw(
    n_hours: int = 48,
    year: int = 2005,
    city: str = "TestCity",
    lat: float = -34.6,
    lon: float = -58.4,
    tz: float = -3.0,
    elev_m: float = 25.0,
) -> EpwFile:
    """
    Construye un EPW sintético de n_hours consecutivas desde 1-ene hour=1.
    Útil para tests.
    """
    header = [
        f"LOCATION,{city},TestState,ARG,Custom,999999,{lat},{lon},{tz},{elev_m}",
        "DESIGN CONDITIONS,0",
        "TYPICAL/EXTREME PERIODS,0",
        "GROUND TEMPERATURES,0",
        "HOLIDAYS/DAYLIGHT SAVINGS,No,0,0,0",
        "COMMENTS 1,Synthetic EPW for unit tests",
        "COMMENTS 2,",
        f"DATA PERIODS,1,1,Data,Sunday,1/1,{_end_date_for_hours(n_hours)}",
    ]

    rows = []
    # Generar horas 1..24 por día desde 1-ene
    month, day, hour = 1, 1, 1
    for _ in range(n_hours):
        row = [""] * EPW_N_FIELDS
        row[EPW_YEAR] = str(year)
        row[EPW_MONTH] = str(month)
        row[EPW_DAY] = str(day)
        row[EPW_HOUR] = str(hour)
        row[EPW_MINUTE] = "0"
        row[EPW_DATA_SOURCE] = "?" * 23  # placeholder flags
        row[EPW_DRY_BULB] = "20.0"
        row[EPW_DEW_POINT] = "10.0"
        row[EPW_RH] = "50"
        row[EPW_PRESSURE] = "101325"
        row[EPW_ET_HORIZ] = "0"
        row[EPW_ET_DIRECT] = "0"
        row[EPW_IR_HORIZ] = "300"
        row[EPW_GHI] = "100"
        row[EPW_DNI] = "50"
        row[EPW_DHI] = "50"
        for i in range(EPW_GLO_ILLUM, EPW_N_FIELDS):
            row[i] = "0"
        row[EPW_WIND_DIR] = "180"
        row[EPW_WIND_SPEED] = "2.0"
        rows.append(row)

        hour += 1
        if hour > 24:
            hour = 1
            day += 1
            # Solo enero en fixtures cortos
            if day > 31:
                day = 1
                month += 1

    cols = [f"field_{i}" for i in range(EPW_N_FIELDS)]
    df = pd.DataFrame(rows, columns=cols, dtype=object)
    for idx in (EPW_YEAR, EPW_MONTH, EPW_DAY, EPW_HOUR, EPW_MINUTE):
        df[f"field_{idx}"] = pd.to_numeric(df[f"field_{idx}"], errors="coerce")

    return EpwFile(
        header_lines=header,
        data=df,
        location=_parse_location(header[0]),
        n_fields=EPW_N_FIELDS,
    )


def _end_date_for_hours(n_hours: int) -> str:
    days = (n_hours + 23) // 24
    return f"1/{min(days, 31)}"
