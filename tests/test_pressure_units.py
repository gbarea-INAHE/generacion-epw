"""Tests de normalización de presión a kPa."""
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
from preprocessor import normalize_pressure_to_kpa


def test_normalize_pressure_kpa_unchanged():
    s = pd.Series([96.95, 97.1, 95.0])
    out = normalize_pressure_to_kpa(s)
    assert out.iloc[0] == pytest.approx(96.95)


def test_normalize_pressure_pa_to_kpa():
    s = pd.Series([96950.0, 93159.0, 101325.0])
    out = normalize_pressure_to_kpa(s)
    assert out.iloc[0] == pytest.approx(96.95)
    assert out.iloc[2] == pytest.approx(101.325)


def test_normalize_pressure_hpa_to_kpa():
    s = pd.Series([969.5, 1013.25, 930.0])
    out = normalize_pressure_to_kpa(s)
    assert out.iloc[0] == pytest.approx(96.95)
    assert out.iloc[1] == pytest.approx(101.325)


def test_fill_keeps_plantilla_pressure_as_kpa():
    """Regresión: 96.95 kPa no debe terminar como 9.695 kPa."""
    rows = [{
        COL_DATETIME: "2005-01-01 12:00:00",
        COL_GHI: 600.0,
        COL_DNI: np.nan,
        COL_DHI: np.nan,
        COL_DRY_BULB: 28.0,
        COL_PRESSURE: 96.95,
        COL_RH: 40.0,
    }]
    df = pd.DataFrame(rows)
    df[COL_DATETIME] = pd.to_datetime(df[COL_DATETIME])
    md = MeasuredData(df=df, source_name="t")
    result = fill_missing_solar(md, -32.833, -68.783, -3.0, primary="Erbs")
    assert result.df["pressure_kPa"].iloc[0] == pytest.approx(96.95)
