"""Test de integración: plantilla parcial + EPW → EPW modificado."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from epw_io import EPW_GHI, EPW_DNI, make_minimal_epw, write_epw, read_epw
from epw_merge import build_modified_epw_bytes, merge_into_epw
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
import io


def test_end_to_end_partial_year_merge():
    rows = []
    for h in range(10, 14):
        rows.append({
            COL_DATETIME: pd.Timestamp(f"2005-01-01 {h:02d}:00:00"),
            COL_GHI: 500.0 + 10 * h,
            COL_DNI: np.nan,
            COL_DHI: np.nan,
            COL_DRY_BULB: 22.0,
            COL_PRESSURE: 101.0,
            COL_RH: 45.0,
        })
    # Una hora con DNI medido
    rows[1][COL_DNI] = 700.0

    md = MeasuredData(df=pd.DataFrame(rows), source_name="partial")
    fill = fill_missing_solar(md, -34.6, -58.4, -3.0, primary="Erbs")
    epw = make_minimal_epw(n_hours=48)
    ghi_untouched = float(epw.data.iloc[0][f"field_{EPW_GHI}"])  # hour 1 = 00:00

    merged, report = merge_into_epw(epw, fill)
    assert report.hours_matched == 4
    assert report.n_ghi_overwritten == 4
    assert report.n_dni_overwritten == 4
    # Hora 00:00 del EPW (índice 0) no tocada
    assert float(merged.data.iloc[0][f"field_{EPW_GHI}"]) == pytest.approx(ghi_untouched)

    # Round-trip bytes
    raw = build_modified_epw_bytes(merged)
    reloaded = read_epw(io.BytesIO(raw))
    assert reloaded.n_hours == 48
    # Hour 11 start → EPW hour 12 → index 11
    assert float(reloaded.data.iloc[11][f"field_{EPW_DNI}"]) == pytest.approx(700.0)
