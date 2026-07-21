"""Tests de merge parcial medidos → EPW."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from epw_io import (
    EPW_DHI,
    EPW_DNI,
    EPW_DRY_BULB,
    EPW_GHI,
    EPW_PRESSURE,
    EPW_RH,
    make_minimal_epw,
)
from epw_merge import merge_into_epw, template_start_to_epw_hour
from fill_components import FillResult


def test_template_start_to_epw_hour_mapping():
    assert template_start_to_epw_hour(pd.Timestamp("2005-01-01 00:00:00")) == (1, 1, 1)
    assert template_start_to_epw_hour(pd.Timestamp("2005-01-01 23:00:00")) == (1, 1, 24)
    assert template_start_to_epw_hour(pd.Timestamp("2005-01-02 00:00:00")) == (1, 2, 1)


def _fill_from_rows(rows: list[dict]) -> FillResult:
    df = pd.DataFrame(rows)
    summary = {
        "rows_total": float(len(df)),
        "rows_filled_dni": float(df.get("filled_dni", pd.Series(dtype=bool)).sum()
                                 if "filled_dni" in df else 0),
        "rows_filled_dhi": float(df.get("filled_dhi", pd.Series(dtype=bool)).sum()
                                 if "filled_dhi" in df else 0),
    }
    return FillResult(df=df, summary=summary, warnings=[])


def test_partial_overwrite_preserves_unmatched_hours():
    epw = make_minimal_epw(n_hours=48)
    ghi_before_h2 = float(epw.data.iloc[1][f"field_{EPW_GHI}"])  # hour 2
    dry_before_h2 = float(epw.data.iloc[1][f"field_{EPW_DRY_BULB}"])

    fill = _fill_from_rows([{
        "timestamp_start": pd.Timestamp("2005-01-01 00:00:00"),  # → EPW hour 1
        "GHI_out": 555.0,
        "DNI_out": 400.0,
        "DHI_out": 155.0,
        "temp_C": 25.0,
        "pressure_kPa": 100.0,
        "RH_measured": 60.0,
        "filled_dni": True,
        "filled_dhi": True,
    }])

    merged, report = merge_into_epw(epw, fill)
    assert report.hours_matched == 1
    assert report.n_ghi_overwritten == 1
    assert float(merged.data.iloc[0][f"field_{EPW_GHI}"]) == pytest.approx(555.0)
    assert float(merged.data.iloc[0][f"field_{EPW_DNI}"]) == pytest.approx(400.0)
    assert float(merged.data.iloc[0][f"field_{EPW_DHI}"]) == pytest.approx(155.0)
    assert float(merged.data.iloc[0][f"field_{EPW_DRY_BULB}"]) == pytest.approx(25.0)
    # kPa → Pa
    assert float(merged.data.iloc[0][f"field_{EPW_PRESSURE}"]) == pytest.approx(100000.0)
    assert float(merged.data.iloc[0][f"field_{EPW_RH}"]) == pytest.approx(60.0)

    # Hora 2 intacta
    assert float(merged.data.iloc[1][f"field_{EPW_GHI}"]) == pytest.approx(ghi_before_h2)
    assert float(merged.data.iloc[1][f"field_{EPW_DRY_BULB}"]) == pytest.approx(dry_before_h2)


def test_nan_values_do_not_overwrite():
    epw = make_minimal_epw(n_hours=24)
    dni_before = float(epw.data.iloc[0][f"field_{EPW_DNI}"])
    fill = _fill_from_rows([{
        "timestamp_start": pd.Timestamp("2005-01-01 00:00:00"),
        "GHI_out": 200.0,
        "DNI_out": np.nan,
        "DHI_out": np.nan,
        "temp_C": np.nan,
        "pressure_kPa": np.nan,
        "RH_measured": np.nan,
    }])
    merged, report = merge_into_epw(epw, fill)
    assert report.n_ghi_overwritten == 1
    assert report.n_dni_overwritten == 0
    assert float(merged.data.iloc[0][f"field_{EPW_DNI}"]) == pytest.approx(dni_before)


def test_unmatched_hour_counted():
    epw = make_minimal_epw(n_hours=24)  # solo enero días 1
    fill = _fill_from_rows([{
        "timestamp_start": pd.Timestamp("2005-06-15 12:00:00"),
        "GHI_out": 100.0,
        "DNI_out": 50.0,
        "DHI_out": 50.0,
        "temp_C": 20.0,
        "pressure_kPa": 101.0,
        "RH_measured": 50.0,
    }])
    _, report = merge_into_epw(epw, fill)
    assert report.hours_matched == 0
    assert report.hours_unmatched_measured == 1
