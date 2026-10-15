"""Tests de branding y tema visual."""
from __future__ import annotations

from branding import (
    AUTHORS,
    CTA_DECOMP_DESC,
    DECOMP_MODELS_BULLETS,
    DECOMP_MODELS_INFO,
    DECOMP_SIDEBAR_CAPTION,
    LOGO_PATH,
    PRODUCT_NAME,
    TAGLINE,
    logo_exists,
)
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


def test_mode_route_constants():
    from branding import MODE_DECOMP, MODE_EPW, MODE_HOME
    assert MODE_HOME == "home"
    assert MODE_DECOMP == "decomp"
    assert MODE_EPW == "epw"


def test_decomp_copy_matches_solar_decomp_v110():
    """Textos del modo Descomposición alineados a Solar Decomp v1.1.0."""
    assert "3 modelos en paralelo" in DECOMP_MODELS_INFO
    assert "columnas separadas" in DECOMP_MODELS_INFO
    assert "Reindl-2" in DECOMP_MODELS_BULLETS
    assert "Perez et al., 1992" in DECOMP_MODELS_BULLETS
    assert "pvlib" in DECOMP_MODELS_BULLETS
    assert "agua precipitable desconocida" in DECOMP_MODELS_BULLETS
    assert "DIRINT" in DECOMP_SIDEBAR_CAPTION and "Reindl-2" in DECOMP_SIDEBAR_CAPTION
    assert "Perez 1992" in CTA_DECOMP_DESC
    assert "Reindl-2" in CTA_DECOMP_DESC


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
