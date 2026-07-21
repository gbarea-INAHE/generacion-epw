"""Tests de plantilla y carga de medidos."""
from __future__ import annotations

import io

import pandas as pd
import pytest

from measured_template import (
    COL_DATETIME,
    COL_DHI,
    COL_DNI,
    COL_GHI,
    COL_WIND_SPD,
    generate_template_xlsx,
    load_measured_table,
    save_template_xlsx,
)


def test_generate_and_load_template(tmp_path):
    path = save_template_xlsx(tmp_path / "plantilla.xlsx", n_hours=48)
    assert path.exists()
    md = load_measured_table(path)
    assert len(md.df) == 48
    assert COL_DATETIME in md.df.columns
    assert COL_GHI in md.df.columns
    assert COL_WIND_SPD in md.df.columns
    assert md.df[COL_GHI].isna().all()


def test_load_with_aliases_csv():
    csv = (
        "Fecha,GHI,DNI,DHI,Dry Bulb,Pressure,RH\n"
        "2005-01-01 00:00:00,100,,,20,101.3,50\n"
        "2005-01-01 01:00:00,200,150,,21,101.2,55\n"
    )
    md = load_measured_table(io.BytesIO(csv.encode("utf-8")), filename="m.csv")
    assert COL_GHI in md.mapped_columns or COL_GHI in md.df.columns
    assert md.df[COL_GHI].iloc[0] == pytest.approx(100)
    assert pd.isna(md.df[COL_DNI].iloc[0])
    assert md.df[COL_DNI].iloc[1] == pytest.approx(150)


def test_designbuilder_datetime_format():
    csv = (
        "Date/Time,Global Solar Wh/m2,Normal Solar Wh/m2,Diffuse Solar Wh/m2\n"
        "2005/01/01 @ 00:00:00,10,,\n"
    )
    md = load_measured_table(io.BytesIO(csv.encode("utf-8")), filename="t.csv")
    assert md.df[COL_DATETIME].iloc[0].hour == 0
    assert md.df[COL_GHI].iloc[0] == pytest.approx(10)


def test_future_cols_present_but_ignored_in_stage1_list():
    from measured_template import FUTURE_COLS, STAGE1_MERGE_COLS
    assert COL_WIND_SPD in FUTURE_COLS
    assert COL_WIND_SPD not in STAGE1_MERGE_COLS
    assert COL_DHI in STAGE1_MERGE_COLS


def test_template_xlsx_bytes_roundtrip():
    raw = generate_template_xlsx(n_hours=24)
    md = load_measured_table(io.BytesIO(raw), filename="plantilla_medidos_epw.xlsx")
    assert len(md.df) == 24
