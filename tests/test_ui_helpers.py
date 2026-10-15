"""Helpers de UI / robustez de resultados."""
from __future__ import annotations

import pandas as pd

from app_solar import _styled_or_plain


def test_styled_or_plain_returns_dataframe_or_styler():
    df = pd.DataFrame({"a": [1.234, 2.0], "b": [3.0, None]})
    out = _styled_or_plain(df, {"a": "{:.1f}", "b": "{:.1f}"})
    # Con jinja2 → Styler; sin jinja2 → DataFrame. Ambos son aceptables.
    assert out is not None
    assert hasattr(out, "data") or isinstance(out, pd.DataFrame)
