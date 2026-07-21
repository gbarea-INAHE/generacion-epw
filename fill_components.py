"""
fill_components.py — Completa DNI/DHI faltantes conservando valores medidos.

Envuelve el pipeline preprocessor + decomposition con lógica preserve_existing
(como el legado fill_missing_solar_components).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from decomposition import run_decomposition
from io_handler import LoadedData, detect_resolution_sec
from measured_template import (
    COL_DATETIME,
    COL_DHI,
    COL_DNI,
    COL_DRY_BULB,
    COL_GHI,
    COL_PRESSURE,
    COL_RH,
    MeasuredData,
)
from preprocessor import aggregate_to_hourly


@dataclass
class FillResult:
    """Resultado del fill selectivo de componentes solares."""

    df: pd.DataFrame
    summary: dict
    warnings: list[str] = field(default_factory=list)


def _measured_to_loaded(md: MeasuredData) -> tuple[LoadedData, pd.DataFrame]:
    """
    Convierte MeasuredData a LoadedData para el preprocessor.
    Retorna también un DF horario crudo con DNI/DHI/RH medidos por hora.
    """
    df = md.df.copy()
    df = df[df[COL_DATETIME].notna()].copy()
    if df.empty:
        raise ValueError("La plantilla no tiene filas con fecha válida.")

    df["_timestamp"] = pd.to_datetime(df[COL_DATETIME])
    # GHI: si no hay columna útil, crear NaN (no se descompone esas horas)
    if COL_GHI not in df.columns:
        df[COL_GHI] = np.nan

    try:
        resolution_sec = detect_resolution_sec(df["_timestamp"])
    except ValueError:
        resolution_sec = 3600

    temp_col = COL_DRY_BULB if df[COL_DRY_BULB].notna().any() else None
    pressure_col = COL_PRESSURE if df[COL_PRESSURE].notna().any() else None

    # Si no hay ningún GHI válido, igual armamos LoadedData con columna GHI
    # (aggregate marcará horas inválidas).
    ld = LoadedData(
        df=df,
        timestamp_col=COL_DATETIME,
        ghi_col=COL_GHI,
        resolution_sec=resolution_sec,
        dni_col=COL_DNI,
        dhi_col=COL_DHI,
        temp_col=temp_col,
        pressure_col=pressure_col,
        warnings=list(md.warnings),
    )

    # Serie horaria de componentes medidos (para preserve)
    df["_hour_key"] = df["_timestamp"].dt.floor("h")
    measured_hourly = df.groupby("_hour_key").agg({
        COL_DNI: "mean",
        COL_DHI: "mean",
        COL_RH: "mean",
        COL_GHI: "mean",
        COL_DRY_BULB: "mean",
        COL_PRESSURE: "mean",
    }).reset_index().rename(columns={"_hour_key": "timestamp_start"})

    return ld, measured_hourly


def fill_missing_solar(
    md: MeasuredData,
    lat_deg: float,
    lon_deg: float,
    tz_hr: float,
    primary: str = "DIRINT",
    preserve_existing: bool = True,
) -> FillResult:
    """
    Agrega a horario, descompone GHI→DNI+DHI y rellena solo huecos.

    Reglas:
      - Si hay GHI y falta DNI y/o DHI → calcular y completar.
      - Si DNI/DHI ya medidos y preserve_existing → se conservan.
      - Si no hay GHI → no se inventa; DNI/DHI medidos se propagan igual.
    """
    warnings: list[str] = list(md.warnings)
    ld, measured_hourly = _measured_to_loaded(md)

    df_hourly = aggregate_to_hourly(ld, lat_deg=lat_deg, lon_deg=lon_deg, tz_hr=tz_hr)

    # Unir medidos DNI/DHI/RH
    df_hourly = df_hourly.merge(
        measured_hourly[
            ["timestamp_start", COL_DNI, COL_DHI, COL_RH]
        ].rename(columns={
            COL_DNI: "DNI_measured",
            COL_DHI: "DHI_measured",
            COL_RH: "RH_measured",
        }),
        on="timestamp_start",
        how="left",
    )

    # Plantilla: presión canónica en kPa — sobrescribe cualquier auto-detección
    if measured_hourly[COL_PRESSURE].notna().any():
        df_hourly = df_hourly.drop(columns=["pressure_kPa"], errors="ignore")
        df_hourly = df_hourly.merge(
            measured_hourly[["timestamp_start", COL_PRESSURE]].rename(
                columns={COL_PRESSURE: "pressure_kPa"}
            ),
            on="timestamp_start",
            how="left",
        )

    # Descomponer solo tiene sentido con GHI; run_decomposition maneja NaN
    df_decomp = run_decomposition(df_hourly, primary=primary)

    dni_meas = df_decomp["DNI_measured"]
    dhi_meas = df_decomp["DHI_measured"]
    need_dni = dni_meas.isna() if preserve_existing else pd.Series(True, index=df_decomp.index)
    need_dhi = dhi_meas.isna() if preserve_existing else pd.Series(True, index=df_decomp.index)

    # No rellenar desde modelo si GHI_h es NaN (no hay base para descomponer)
    no_ghi = df_decomp["GHI_h"].isna()
    need_dni = need_dni & ~no_ghi
    need_dhi = need_dhi & ~no_ghi

    dni_final = dni_meas.copy()
    dhi_final = dhi_meas.copy()
    dni_final = dni_final.where(~need_dni, df_decomp["DNI"])
    dhi_final = dhi_final.where(~need_dhi, df_decomp["DHI"])

    df_decomp["DNI_final"] = dni_final
    df_decomp["DHI_final"] = dhi_final
    df_decomp["filled_dni"] = need_dni
    df_decomp["filled_dhi"] = need_dhi
    # Columnas amigables para merge EPW
    df_decomp["GHI_out"] = df_decomp["GHI_h"]
    df_decomp["DNI_out"] = dni_final
    df_decomp["DHI_out"] = dhi_final

    n_filled_dni = int(need_dni.sum())
    n_filled_dhi = int(need_dhi.sum())
    n_preserved_dni = int((~dni_meas.isna()).sum())
    n_preserved_dhi = int((~dhi_meas.isna()).sum())

    if no_ghi.any():
        warnings.append(
            f"{int(no_ghi.sum())} horas sin GHI válido: no se descompuso "
            "(sí se mergean DNI/DHI/meteo medidos si existen)."
        )

    summary = {
        "rows_total": float(len(df_decomp)),
        "rows_filled_dni": float(n_filled_dni),
        "rows_filled_dhi": float(n_filled_dhi),
        "rows_preserved_dni": float(n_preserved_dni),
        "rows_preserved_dhi": float(n_preserved_dhi),
        "primary_model": primary,
    }
    return FillResult(df=df_decomp, summary=summary, warnings=warnings)
