"""Tests de lectura/escritura EPW."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from epw_io import (
    EPW_DRY_BULB,
    EPW_GHI,
    EPW_HOUR,
    EPW_MONTH,
    make_minimal_epw,
    read_epw,
    write_epw,
)


def test_make_minimal_epw_location_and_hours():
    epw = make_minimal_epw(n_hours=48, city="BsAs", lat=-34.6, lon=-58.4, tz=-3.0)
    assert epw.n_hours == 48
    assert epw.location["city"] == "BsAs"
    assert epw.location["latitude"] == pytest.approx(-34.6)
    assert float(epw.data.iloc[0][f"field_{EPW_HOUR}"]) == 1
    assert float(epw.data.iloc[23][f"field_{EPW_HOUR}"]) == 24
    assert float(epw.data.iloc[24][f"field_{EPW_MONTH}"]) == 1


def test_epw_round_trip_preserves_data(tmp_path: Path):
    epw = make_minimal_epw(n_hours=24)
    epw.data.loc[0, f"field_{EPW_GHI}"] = "432"
    epw.data.loc[0, f"field_{EPW_DRY_BULB}"] = "21.5"

    path = tmp_path / "test.epw"
    text = write_epw(epw, path)
    assert path.exists()
    assert "LOCATION,TestCity" in text

    loaded = read_epw(path)
    assert loaded.n_hours == 24
    assert len(loaded.header_lines) == len(epw.header_lines)
    assert loaded.header_lines[0] == epw.header_lines[0]
    assert str(loaded.data.iloc[0][f"field_{EPW_GHI}"]) in ("432", "432.0")
    assert float(loaded.data.iloc[0][f"field_{EPW_DRY_BULB}"]) == pytest.approx(21.5)


def test_read_epw_from_string_io():
    import io

    epw = make_minimal_epw(n_hours=2)
    text = write_epw(epw)
    loaded = read_epw(io.StringIO(text))
    assert loaded.n_hours == 2
    assert loaded.location["city"] == "TestCity"


def test_write_then_read_numeric_types():
    epw = make_minimal_epw(n_hours=3)
    text = write_epw(epw)
    loaded = read_epw(__import__("io").StringIO(text))
    assert pd.api.types.is_numeric_dtype(loaded.data[f"field_{EPW_HOUR}"])
    assert list(loaded.data[f"field_{EPW_HOUR}"].astype(int)) == [1, 2, 3]


def test_set_location_timezone():
    from epw_io import set_location_timezone

    epw = make_minimal_epw(n_hours=2, tz=-4.0)
    assert epw.location["tz"] == pytest.approx(-4.0)
    updated = set_location_timezone(epw, -3.0)
    assert updated.location["tz"] == pytest.approx(-3.0)
    assert ",-3.0," in updated.header_lines[0] or updated.header_lines[0].split(",")[8] == "-3.0"


def test_stamp_generation_comments():
    from branding import epw_attribution_comments
    from epw_io import stamp_generation_comments

    epw = make_minimal_epw(n_hours=2)
    c1, c2 = epw_attribution_comments()
    stamped = stamp_generation_comments(epw, c1, c2)
    comments = [h for h in stamped.header_lines if h.upper().startswith("COMMENTS")]
    assert any("Generacion de EPW" in h or "Generación de EPW" in h for h in comments)
    assert any("Barea" in h for h in comments)
    assert any("Ganem" in h for h in comments)
    # Una sola coma de separador de campo al inicio del valor
    assert comments[0].startswith("COMMENTS 1,")
    assert comments[1].startswith("COMMENTS 2,")
