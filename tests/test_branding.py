"""Tests de branding y tema visual."""
from __future__ import annotations

from branding import AUTHORS, LOGO_PATH, PRODUCT_NAME, TAGLINE, logo_exists
from theme import COLOR_ACCENT, css_block


def test_logo_exists():
    assert logo_exists(), f"Falta logo en {LOGO_PATH}"
    assert LOGO_PATH.stat().st_size > 1000


def test_authors_complete():
    assert len(AUTHORS) >= 2
    for a in AUTHORS:
        assert a.name
        assert "@" in a.email
        assert a.title


def test_product_copy():
    assert PRODUCT_NAME == "Generación de EPW"
    assert "EPW" in TAGLINE or "solar" in TAGLINE.lower()


def test_authors_affiliation_short():
    for a in AUTHORS:
        assert a.title == "INAHE - CONICET"
        assert "Investigador" not in a.title


def test_css_contains_brand_tokens():
    css = css_block(home=True)
    assert "Fraunces" in css
    assert "DM Sans" in css
    assert COLOR_ACCENT in css
    assert "sd-fade-up" in css
    assert "stSidebar" in css  # oculto en home


def test_css_sidebar_controls_dark():
    css = css_block(home=False)
    assert "stFileUploaderDropzone" in css
    assert "#2C3E48" in css or "sd-sidebar-ctrl" in css
    assert "stDecoration" in css
