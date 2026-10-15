"""
ui_home.py — Portada institucional Generación de EPW.
"""
from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from branding import (
    AUTHORS,
    CTA_DECOMP_BUTTON,
    CTA_DECOMP_DESC,
    CTA_DECOMP_TITLE,
    CTA_EPW_BUTTON,
    CTA_EPW_DESC,
    CTA_EPW_TITLE,
    DISCLAIMER,
    INSTITUTION,
    LOGO_PATH,
    MODE_DECOMP,
    MODE_EPW,
    MODE_HOME,
    PRODUCT_NAME,
    SUPPORTING,
    TAGLINE,
    logo_exists,
)
from theme import inject_css


def _logo_data_uri() -> str | None:
    if not logo_exists():
        return None
    raw = Path(LOGO_PATH).read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def _render_html(html: str) -> None:
    """Renderiza HTML sin pasar por el parser Markdown (evita bloques de código)."""
    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html.replace("\n", ""), unsafe_allow_html=True)


def render_home() -> None:
    """Portada: marca, explicación, dos accesos y autores."""
    inject_css(home=True)

    logo_uri = _logo_data_uri()
    logo_html = (
        f'<img src="{logo_uri}" alt="Logo INAHE-CONICET" />'
        if logo_uri
        else '<div class="sd-brand-meta">INAHE</div>'
    )

    _render_html(
        f'<div class="sd-brand-bar">{logo_html}'
        f'<div class="sd-brand-meta">{INSTITUTION}</div></div>'
        f'<div class="sd-hero"><h1>{PRODUCT_NAME}</h1>'
        f'<p class="sd-tagline">{TAGLINE}</p>'
        f'<p class="sd-support">{SUPPORTING}</p></div>'
    )

    st.markdown("##### Elegí una herramienta")
    col1, col2 = st.columns(2, gap="large")

    with col1:
        _render_html(
            f'<div class="sd-cta-wrap">'
            f'<div class="sd-cta"><h3>{CTA_DECOMP_TITLE}</h3>'
            f'<p>{CTA_DECOMP_DESC}</p></div></div>'
        )
        if st.button(
            CTA_DECOMP_BUTTON,
            type="primary",
            use_container_width=True,
            key="cta_decomp",
        ):
            st.session_state.app_page = MODE_DECOMP
            st.query_params["page"] = MODE_DECOMP
            st.rerun()

    with col2:
        _render_html(
            f'<div class="sd-cta-wrap">'
            f'<div class="sd-cta"><h3>{CTA_EPW_TITLE}</h3>'
            f'<p>{CTA_EPW_DESC}</p></div></div>'
        )
        if st.button(
            CTA_EPW_BUTTON,
            type="primary",
            use_container_width=True,
            key="cta_epw",
        ):
            st.session_state.app_page = MODE_EPW
            st.query_params["page"] = MODE_EPW
            st.rerun()

    st.markdown("### Autores")
    a1, a2 = st.columns(2)
    for col, author in zip((a1, a2), AUTHORS):
        with col:
            st.markdown(f"**{author.name}**")
            st.caption(author.title)
            st.markdown(f"[{author.email}](mailto:{author.email})")

    _render_html(f'<div class="sd-footer">{DISCLAIMER}</div>')


def render_back_to_home() -> None:
    """Botón compacto para volver a la portada (sidebar o panel)."""
    if st.button("← Volver a portada", use_container_width=True, key="nav_home"):
        st.session_state.app_page = MODE_HOME
        st.query_params["page"] = MODE_HOME
        st.rerun()
