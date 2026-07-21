"""
epw_merge.py — Alinea medidos (post-fill) con EPW y sobrescribe campos etapa 1.

Convención temporal:
  - Plantilla: timestamp = inicio del intervalo [t, t+1h].
  - EPW EnergyPlus: Hour 1..24 = hour-ending → Hour = start_hour + 1
    (00:00 → Hour 1; 23:00 → Hour 24).

Merge parcial: solo horas con valor medido/calculado válido; resto intacto.
Flags de fuente EPW: se preservan (no se modifican).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from epw_io import (
    EPW_DHI,
    EPW_DNI,
    EPW_DRY_BULB,
    EPW_GHI,
    EPW_HOUR,
    EPW_MINUTE,
    EPW_MONTH,
    EPW_DAY,
    EPW_PRESSURE,
    EPW_RH,
    EPW_YEAR,
    EpwFile,
    write_epw,
)
from fill_components import FillResult
from measured_template import COL_DRY_BULB, COL_PRESSURE, COL_RH


@dataclass
class MergeReport:
    epw_hours_total: int = 0
    measured_hours: int = 0
    hours_matched: int = 0
    hours_unmatched_measured: int = 0
    n_ghi_overwritten: int = 0
    n_dni_overwritten: int = 0
    n_dhi_overwritten: int = 0
    n_dry_bulb_overwritten: int = 0
    n_pressure_overwritten: int = 0
    n_rh_overwritten: int = 0
    n_dni_filled_by_model: int = 0
    n_dhi_filled_by_model: int = 0
    warnings: list[str] = field(default_factory=list)
    fields_touched: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def template_start_to_epw_hour(ts: pd.Timestamp) -> tuple[int, int, int]:
    """
    Convierte timestamp de inicio de intervalo plantilla → (month, day, epw_hour).

    Ejemplo: 2005-01-01 00:00 → (1, 1, 1)
             2005-01-01 23:00 → (1, 1, 24)
    """
    start = pd.Timestamp(ts).floor("h")
    epw_hour = int(start.hour) + 1
    month = int(start.month)
    day = int(start.day)
    if epw_hour == 24:
        # Sigue siendo el mismo día civil del inicio (23:00–24:00 del día D)
        pass
    return month, day, epw_hour


def _valid_num(val) -> bool:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return False
    try:
        float(val)
        return not pd.isna(val)
    except (TypeError, ValueError):
        return False


def _valid_rad(val) -> bool:
    return _valid_num(val) and float(val) >= 0


def _set_field(df: pd.DataFrame, idx, field_i: int, value: float) -> None:
    """Asigna valor numérico como object/str compatible con columnas EPW."""
    col = f"field_{field_i}"
    if df[col].dtype == object:
        df.at[idx, col] = value
    else:
        # Forzar a object si la columna es string-arrow
        df[col] = df[col].astype(object)
        df.at[idx, col] = value


def merge_into_epw(
    epw: EpwFile,
    fill: FillResult,
    overwrite_meteo: bool = True,
) -> tuple[EpwFile, MergeReport]:
    """
    Sobrescribe campos etapa 1 del EPW con la salida de fill_missing_solar.

    No muta el EpwFile de entrada: trabaja sobre una copia.
    """
    out = EpwFile(
        header_lines=list(epw.header_lines),
        data=epw.data.copy(),
        location=dict(epw.location),
        n_fields=epw.n_fields,
    )
    # Asegurar object dtype en campos modificables (compat pandas string-arrow)
    for i in range(out.n_fields):
        if i not in (EPW_YEAR, EPW_MONTH, EPW_DAY, EPW_HOUR, EPW_MINUTE):
            out.data[f"field_{i}"] = out.data[f"field_{i}"].astype(object)
    report = MergeReport(
        epw_hours_total=epw.n_hours,
        n_dni_filled_by_model=int(fill.summary.get("rows_filled_dni", 0)),
        n_dhi_filled_by_model=int(fill.summary.get("rows_filled_dhi", 0)),
        warnings=list(fill.warnings),
    )

    df_m = fill.df.copy()
    report.measured_hours = len(df_m)

    # Índice EPW por (month, day, hour)
    epw_keys = {}
    for i, row in out.data.iterrows():
        key = (
            int(row[f"field_{EPW_MONTH}"]),
            int(row[f"field_{EPW_DAY}"]),
            int(row[f"field_{EPW_HOUR}"]),
        )
        epw_keys[key] = i

    matched = 0
    unmatched = 0
    touched = set()

    for _, mrow in df_m.iterrows():
        ts = mrow["timestamp_start"]
        month, day, hour = template_start_to_epw_hour(ts)
        key = (month, day, hour)
        if key not in epw_keys:
            unmatched += 1
            continue
        matched += 1
        idx = epw_keys[key]

        # Radiación
        if _valid_rad(mrow.get("GHI_out", np.nan)):
            _set_field(out.data, idx, EPW_GHI, float(mrow["GHI_out"]))
            report.n_ghi_overwritten += 1
            touched.add("GHI")

        if _valid_rad(mrow.get("DNI_out", np.nan)):
            _set_field(out.data, idx, EPW_DNI, float(mrow["DNI_out"]))
            report.n_dni_overwritten += 1
            touched.add("DNI")

        if _valid_rad(mrow.get("DHI_out", np.nan)):
            _set_field(out.data, idx, EPW_DHI, float(mrow["DHI_out"]))
            report.n_dhi_overwritten += 1
            touched.add("DHI")

        if overwrite_meteo:
            temp = mrow.get("temp_C", np.nan)
            if _valid_num(temp):
                _set_field(out.data, idx, EPW_DRY_BULB, float(temp))
                report.n_dry_bulb_overwritten += 1
                touched.add("DryBulb")

            pk = mrow.get("pressure_kPa", np.nan)
            if _valid_num(pk):
                _set_field(out.data, idx, EPW_PRESSURE, float(pk) * 1000.0)
                report.n_pressure_overwritten += 1
                touched.add("Pressure")

            rh = mrow.get("RH_measured", np.nan)
            if _valid_num(rh):
                _set_field(out.data, idx, EPW_RH, float(rh))
                report.n_rh_overwritten += 1
                touched.add("RH")

    report.hours_matched = matched
    report.hours_unmatched_measured = unmatched
    report.fields_touched = sorted(touched)

    if unmatched:
        report.warnings.append(
            f"{unmatched} horas de la plantilla no coinciden con el EPW "
            f"(mes/día/hora) y se omitieron."
        )
    report.warnings.append(
        f"Merge parcial: {matched}/{report.epw_hours_total} horas del EPW "
        f"recibieron al menos un intento de match; campos: {report.fields_touched}."
    )

    return out, report


def build_modified_epw_bytes(epw: EpwFile) -> bytes:
    """Serializa EPW modificado a bytes UTF-8."""
    return write_epw(epw).encode("utf-8")
