"""
measured_template.py — Plantilla de datos medidos y carga/validación.

Columnas etapa 1 (merge): Date/Time, Dry Bulb, Pressure, RH, GHI, DNI, DHI.
Columnas futuras (plantilla, sin merge): Dew Point, Wind Speed, Wind Direction.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Optional, Union

import numpy as np
import pandas as pd

# ── Nombres canónicos ─────────────────────────────────────────────────────────
COL_DATETIME = "Date/Time"
COL_DRY_BULB = "Dry Bulb Temperature C"
COL_PRESSURE = "Atmospheric Pressure kPa"
COL_RH = "Relative Humidity %"
COL_GHI = "Global Solar Wh/m2"
COL_DNI = "Normal Solar Wh/m2"
COL_DHI = "Diffuse Solar Wh/m2"
# Futuras (no mergeadas en etapa 1)
COL_DEW = "Dew Point Temperature C"
COL_WIND_SPD = "Wind Speed m/s"
COL_WIND_DIR = "Wind Direction deg"

STAGE1_MERGE_COLS = [
    COL_DRY_BULB,
    COL_PRESSURE,
    COL_RH,
    COL_GHI,
    COL_DNI,
    COL_DHI,
]

FUTURE_COLS = [COL_DEW, COL_WIND_SPD, COL_WIND_DIR]

REQUIRED_COLS = [COL_DATETIME]  # GHI no es estrictamente obligatorio por fila

ALIASES = {
    COL_DATETIME: [
        "date/time", "datetime", "fecha", "fecha/hora", "timestamp", "time", "date",
    ],
    COL_DRY_BULB: [
        "dry bulb temperature c", "dry bulb", "tdb", "temp_c", "temperatura",
        "air temperature", "dry_bulb_temperature_c",
    ],
    COL_PRESSURE: [
        "atmospheric pressure kpa", "pressure", "presion", "press_kpa", "p_kpa",
    ],
    COL_RH: [
        "relative humidity %", "relative humidity", "rh", "humidity", "humedad",
    ],
    COL_GHI: [
        "global solar wh/m2", "global solar", "ghi", "global_horizontal_irradiance",
    ],
    COL_DNI: [
        "normal solar wh/m2", "normal solar", "dni", "direct normal",
    ],
    COL_DHI: [
        "diffuse solar wh/m2", "diffuse solar", "dhi", "diffuse horizontal",
    ],
    COL_DEW: [
        "dew point temperature c", "dew point", "tdew", "punto de rocio",
    ],
    COL_WIND_SPD: [
        "wind speed m/s", "wind speed", "ws", "velocidad viento",
    ],
    COL_WIND_DIR: [
        "wind direction deg", "wind direction", "wd", "direccion viento",
    ],
}

_DT_FORMATS = [
    "%Y/%m/%d @ %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
]


@dataclass
class MeasuredData:
    """Datos medidos normalizados a columnas canónicas."""

    df: pd.DataFrame
    source_name: str = ""
    warnings: list[str] = field(default_factory=list)
    mapped_columns: dict = field(default_factory=dict)


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", str(name).strip().lower().replace("_", " "))


def _map_columns(df: pd.DataFrame) -> tuple[dict[str, str], list[str]]:
    """
    Retorna mapping canónico → nombre original y warnings.
    """
    cols_norm = {_norm(c): c for c in df.columns}
    mapped: dict[str, str] = {}
    warnings: list[str] = []

    for canonical, alias_list in ALIASES.items():
        found = None
        for alias in alias_list:
            if alias in cols_norm:
                found = cols_norm[alias]
                break
            # match parcial suave
            for cn, original in cols_norm.items():
                if alias in cn or cn in alias:
                    found = original
                    break
            if found:
                break
        if found:
            mapped[canonical] = found

    if COL_DATETIME not in mapped:
        raise ValueError(
            "No se encontró columna de fecha/hora. "
            f"Esperada: '{COL_DATETIME}' (o aliases: Date/Time, Datetime, Fecha)."
        )

    if COL_GHI not in mapped:
        warnings.append(
            "No se detectó columna GHI; solo se mergearán meteo y DNI/DHI medidos."
        )

    return mapped, warnings


def _parse_datetime(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    # Formato plantilla DesignBuilder: "2005/01/01 @ 00:00:00"
    s = series.astype(str).str.replace("@", " ", regex=False).str.replace(r"\s+", " ", regex=True).str.strip()
    for fmt in _DT_FORMATS:
        try:
            return pd.to_datetime(s, format=fmt, errors="raise")
        except Exception:
            continue
    return pd.to_datetime(s, errors="coerce")


def load_measured_table(
    source: Union[str, Path, BinaryIO],
    filename: str = "",
) -> MeasuredData:
    """Carga CSV o Excel de medidas y normaliza columnas canónicas."""
    name = filename or (getattr(source, "name", "") or str(source))
    name_l = name.lower()

    if hasattr(source, "read"):
        raw = source.read()
        if isinstance(raw, bytes):
            bio = io.BytesIO(raw)
        else:
            bio = io.StringIO(raw)
        if name_l.endswith(".csv"):
            df = pd.read_csv(bio)
        else:
            df = pd.read_excel(bio)
    else:
        path = Path(source)
        name = path.name
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)

    mapped, warnings = _map_columns(df)
    out = pd.DataFrame()
    out[COL_DATETIME] = _parse_datetime(df[mapped[COL_DATETIME]])
    if out[COL_DATETIME].isna().all():
        raise ValueError("No se pudieron parsear las fechas/horas de la plantilla.")

    for col in STAGE1_MERGE_COLS + FUTURE_COLS:
        if col in mapped:
            out[col] = pd.to_numeric(df[mapped[col]], errors="coerce")
        else:
            out[col] = np.nan

    n_bad = int(out[COL_DATETIME].isna().sum())
    if n_bad:
        warnings.append(f"{n_bad} filas con fecha inválida (se ignorarán en el merge).")

    return MeasuredData(
        df=out,
        source_name=name,
        warnings=warnings,
        mapped_columns=mapped,
    )


def build_template_dataframe(year: int = 2005, n_hours: int = 8760) -> pd.DataFrame:
    """Genera DataFrame vacío de plantilla (año no bisiesto por defecto)."""
    if n_hours == 8760:
        idx = pd.date_range(f"{year}-01-01", periods=8760, freq="h")
    else:
        idx = pd.date_range(f"{year}-01-01", periods=n_hours, freq="h")

    df = pd.DataFrame({
        COL_DATETIME: idx.strftime("%Y/%m/%d @ %H:%M:%S"),
        COL_DRY_BULB: np.nan,
        COL_PRESSURE: np.nan,
        COL_RH: np.nan,
        COL_GHI: np.nan,
        COL_DNI: np.nan,
        COL_DHI: np.nan,
        COL_DEW: np.nan,
        COL_WIND_SPD: np.nan,
        COL_WIND_DIR: np.nan,
    })
    return df


def generate_template_xlsx(n_hours: int = 8760, year: int = 2005) -> bytes:
    """Genera bytes de un .xlsx de plantilla con hoja de datos y README."""
    df = build_template_dataframe(year=year, n_hours=n_hours)
    readme = pd.DataFrame({
        "Campo": [
            COL_DATETIME,
            COL_GHI,
            COL_DNI,
            COL_DHI,
            COL_DRY_BULB,
            COL_PRESSURE,
            COL_RH,
            COL_DEW,
            COL_WIND_SPD,
            COL_WIND_DIR,
        ],
        "Obligatorio": [
            "Sí",
            "Recomendado (para descomponer)",
            "Opcional (vacío = calcular)",
            "Opcional (vacío = calcular)",
            "Opcional (merge etapa 1)",
            "Opcional kPa (merge etapa 1 → Pa en EPW)",
            "Opcional (merge etapa 1)",
            "Reservado (sin merge aún)",
            "Reservado (sin merge aún)",
            "Reservado (sin merge aún)",
        ],
        "Notas": [
            "Inicio del intervalo horario [t, t+1h]; geometría en t+30min",
            "Wh/m² ≈ W/m² en paso horario",
            "Se conserva si está medido",
            "Se conserva si está medido",
            "Sobrescribe Dry Bulb del EPW",
            "Convertir: EPW usa Pa (= kPa × 1000)",
            "Sobrescribe RH del EPW",
            "Segunda etapa",
            "Segunda etapa",
            "Segunda etapa",
        ],
    })
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Datos", index=False)
        readme.to_excel(writer, sheet_name="README", index=False)
    return buf.getvalue()


def save_template_xlsx(path: Union[str, Path], n_hours: int = 8760, year: int = 2005) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(generate_template_xlsx(n_hours=n_hours, year=year))
    return path


def template_path_default() -> Path:
    return Path(__file__).resolve().parent / "templates" / "plantilla_medidos_epw.xlsx"
