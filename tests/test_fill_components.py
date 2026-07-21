"""Tests de fill selectivo DNI/DHI."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from fill_components import fill_missing_solar
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


def _md_hours(rows: list[dict]) -> MeasuredData:
    df = pd.DataFrame(rows)
    df[COL_DATETIME] = pd.to_datetime(df[COL_DATETIME])
    for c in (COL_GHI, COL_DNI, COL_DHI, COL_DRY_BULB, COL_PRESSURE, COL_RH):
        if c not in df.columns:
            df[c] = np.nan
    return MeasuredData(df=df, source_name="test")


# Buenos Aires — mediodía claro aproximado (ene)
LAT, LON, TZ = -34.6, -58.4, -3.0


def test_preserve_measured_dni():
    rows = []
    for h in range(10, 14):
        rows.append({
            COL_DATETIME: f"2005-01-15 {h:02d}:00:00",
            COL_GHI: 600.0,
            COL_DNI: 800.0 if h == 12 else np.nan,
            COL_DHI: np.nan,
            COL_DRY_BULB: 28.0,
            COL_PRESSURE: 101.0,
            COL_RH: 40.0,
        })
    md = _md_hours(rows)
    result = fill_missing_solar(md, LAT, LON, TZ, primary="Erbs")
    df = result.df
    # Hora 12: DNI preservado
    row12 = df[df["timestamp_start"].dt.hour == 12].iloc[0]
    assert row12["DNI_out"] == pytest.approx(800.0)
    assert bool(row12["filled_dni"]) is False
    # Otras horas: DNI rellenado
    assert result.summary["rows_filled_dni"] >= 1
    assert result.summary["rows_preserved_dni"] == 1.0


def test_fill_both_when_missing():
    rows = [{
        COL_DATETIME: "2005-01-15 12:00:00",
        COL_GHI: 700.0,
        COL_DNI: np.nan,
        COL_DHI: np.nan,
        COL_DRY_BULB: 30.0,
        COL_PRESSURE: 100.5,
        COL_RH: 35.0,
    }]
    md = _md_hours(rows)
    result = fill_missing_solar(md, LAT, LON, TZ, primary="DIRINT")
    row = result.df.iloc[0]
    assert bool(row["filled_dni"])
    assert bool(row["filled_dhi"])
    assert row["DNI_out"] >= 0
    assert row["DHI_out"] >= 0
    # Balance aproximado
    cos_z = row["G0h"] / row["G0n"] if row["G0n"] > 0 else 0
    recon = row["DNI_out"] * cos_z + row["DHI_out"]
    if recon > 0 and not np.isnan(row["GHI_h"]):
        assert abs(row["GHI_h"] / recon - 1.0) < 0.15


def test_no_ghi_does_not_invent_decomposition():
    rows = [{
        COL_DATETIME: "2005-01-15 12:00:00",
        COL_GHI: np.nan,
        COL_DNI: 100.0,
        COL_DHI: np.nan,
    }]
    md = _md_hours(rows)
    result = fill_missing_solar(md, LAT, LON, TZ)
    row = result.df.iloc[0]
    assert row["DNI_out"] == pytest.approx(100.0)
    assert bool(row["filled_dni"]) is False
    assert pd.isna(row["DHI_out"]) or bool(row["filled_dhi"]) is False
