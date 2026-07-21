"""
theme.py — Tokens visuales y CSS institucional para Streamlit.
"""
from __future__ import annotations

import streamlit as st

# Tokens — laboratorio solar andino / INAHE
COLOR_BG_TOP = "#F7F4EF"
COLOR_BG_BOTTOM = "#E8EEF0"
COLOR_ACCENT = "#C47B0A"
COLOR_ACCENT_HOVER = "#A86808"
COLOR_TEXT = "#1A2B34"
COLOR_MUTED = "#5A6A73"
COLOR_SURFACE = "#FFFFFF"
COLOR_BORDER = "#D5DCE0"
COLOR_SIDEBAR = "#1A2B34"
COLOR_SIDEBAR_CTRL = "#2C3E48"      # fondo controles sidebar (botones / upload)
COLOR_SIDEBAR_CTRL_HOVER = "#3A4F5A"
COLOR_TEAL = "#2A6F7A"
COLOR_SCORE = "#3D8B7A"

PLOTLY_COLORS = {
    "GHI": COLOR_ACCENT,
    "DNI_dirint": COLOR_TEAL,
    "DHI_dirint": "#457B9D",
    "DNI_erbs": "#B85C38",
    "DHI_erbs": "#7BA3B0",
    "Kt": COLOR_TEXT,
    "score": COLOR_SCORE,
}


def css_block(home: bool = False) -> str:
    """CSS global. Si home=True, compacta chrome de Streamlit para la portada."""
    if home:
        layout_rules = f"""
        [data-testid="stSidebar"] {{ display: none !important; }}
        [data-testid="stHeader"] {{
            background: transparent !important;
            height: 0 !important;
        }}
        [data-testid="stToolbar"] {{ display: none !important; }}
        .block-container {{
            padding-top: 2rem !important;
            padding-bottom: 3rem !important;
            max-width: 960px !important;
        }}
        """
    else:
        layout_rules = f"""
        /* Quita la franja blanca que tapa el título */
        [data-testid="stHeader"] {{
            background: transparent !important;
            backdrop-filter: none !important;
        }}
        [data-testid="stDecoration"] {{
            display: none !important;
            background: transparent !important;
        }}
        header[data-testid="stHeader"] {{
            background: transparent !important;
        }}
        .stApp > header {{
            background-color: transparent !important;
        }}
        .block-container {{
            padding-top: 2.75rem !important;
            max-width: 1200px !important;
        }}
        section.main .block-container h1:first-of-type,
        section.main .block-container h2:first-of-type {{
            margin-top: 0.25rem !important;
            padding-top: 0.15rem !important;
        }}
        """

    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&display=swap');

    :root {{
        --sd-accent: {COLOR_ACCENT};
        --sd-accent-hover: {COLOR_ACCENT_HOVER};
        --sd-text: {COLOR_TEXT};
        --sd-muted: {COLOR_MUTED};
        --sd-surface: {COLOR_SURFACE};
        --sd-border: {COLOR_BORDER};
        --sd-bg-top: {COLOR_BG_TOP};
        --sd-bg-bottom: {COLOR_BG_BOTTOM};
        --sd-sidebar-ctrl: {COLOR_SIDEBAR_CTRL};
        --sd-sidebar-ctrl-hover: {COLOR_SIDEBAR_CTRL_HOVER};
    }}

    html, body, [data-testid="stAppViewContainer"] {{
        font-family: "DM Sans", system-ui, sans-serif;
        color: var(--sd-text);
    }}

    [data-testid="stAppViewContainer"] {{
        background:
            radial-gradient(ellipse 80% 50% at 100% -10%, rgba(196,123,10,0.12), transparent 55%),
            radial-gradient(ellipse 60% 40% at -10% 80%, rgba(42,111,122,0.10), transparent 50%),
            linear-gradient(165deg, var(--sd-bg-top) 0%, var(--sd-bg-bottom) 100%);
    }}

    h1, h2, h3, .sd-display {{
        font-family: "Fraunces", Georgia, serif !important;
        color: var(--sd-text) !important;
        letter-spacing: -0.02em;
    }}

    p, label, .stMarkdown, .stCaption {{
        font-family: "DM Sans", system-ui, sans-serif;
    }}

    /* Botones primarios (área principal / portada) */
    div.stButton > button[kind="primary"],
    div.stButton > button[data-testid="baseButton-primary"] {{
        background-color: var(--sd-accent) !important;
        border: 1px solid var(--sd-accent) !important;
        color: #fff !important;
        font-family: "DM Sans", sans-serif !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        transition: background-color 0.2s ease, transform 0.15s ease, box-shadow 0.2s ease;
    }}
    div.stButton > button[kind="primary"]:hover,
    div.stButton > button[data-testid="baseButton-primary"]:hover {{
        background-color: var(--sd-accent-hover) !important;
        border-color: var(--sd-accent-hover) !important;
        color: #fff !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(196,123,10,0.28);
    }}

    section.main div.stButton > button[kind="secondary"],
    section.main div.stButton > button {{
        border-radius: 6px !important;
        border-color: var(--sd-border) !important;
        color: var(--sd-text) !important;
        background: var(--sd-surface) !important;
        font-family: "DM Sans", sans-serif !important;
    }}

    /* ── Sidebar ─────────────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {COLOR_SIDEBAR} 0%, #243944 100%) !important;
        border-right: 1px solid rgba(255,255,255,0.06);
    }}
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown strong,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] .stCaption p {{
        color: #E8EEF0 !important;
    }}
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] .stCaption p {{
        color: #A8B4BC !important;
    }}

    /* Todos los botones del sidebar: gris oscuro + texto blanco */
    [data-testid="stSidebar"] div.stButton > button,
    [data-testid="stSidebar"] div.stDownloadButton > button,
    [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"],
    [data-testid="stSidebar"] button {{
        background-color: var(--sd-sidebar-ctrl) !important;
        background-image: none !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255,255,255,0.14) !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
    }}
    [data-testid="stSidebar"] div.stButton > button *,
    [data-testid="stSidebar"] div.stDownloadButton > button *,
    [data-testid="stSidebar"] button p,
    [data-testid="stSidebar"] button span {{
        color: #FFFFFF !important;
    }}
    [data-testid="stSidebar"] div.stButton > button:hover,
    [data-testid="stSidebar"] div.stDownloadButton > button:hover,
    [data-testid="stSidebar"] button:hover {{
        background-color: var(--sd-sidebar-ctrl-hover) !important;
        border-color: rgba(255,255,255,0.28) !important;
        color: #FFFFFF !important;
    }}
    [data-testid="stSidebar"] div.stButton > button[kind="primary"],
    [data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] {{
        background-color: var(--sd-accent) !important;
        border-color: var(--sd-accent) !important;
        color: #FFFFFF !important;
    }}
    [data-testid="stSidebar"] div.stButton > button[kind="primary"]:hover {{
        background-color: var(--sd-accent-hover) !important;
    }}

    /* File uploader: mismo gris oscuro, texto legible */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] {{
        background: transparent !important;
    }}
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"],
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section {{
        background-color: var(--sd-sidebar-ctrl) !important;
        border: 1px solid rgba(255,255,255,0.14) !important;
        border-radius: 6px !important;
        color: #FFFFFF !important;
    }}
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] *,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section * {{
        color: #E8EEF0 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button {{
        background-color: var(--sd-sidebar-ctrl-hover) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
    }}

    /* Inputs numéricos: fondo oscuro, texto claro */
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] [data-baseweb="input"] ,
    [data-testid="stSidebar"] [data-baseweb="input"] > div,
    [data-testid="stSidebar"] [data-baseweb="select"] > div {{
        background-color: var(--sd-sidebar-ctrl) !important;
        color: #FFFFFF !important;
        border-color: rgba(255,255,255,0.14) !important;
        caret-color: #FFFFFF !important;
    }}
    [data-testid="stSidebar"] input {{
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }}

    /* Checkbox / select labels ya cubiertos; track visible */
    [data-testid="stSidebar"] [data-baseweb="checkbox"] span {{
        color: #E8EEF0 !important;
    }}

    .sd-cta-wrap {{
        min-height: 10.5rem;
        margin-bottom: 0.65rem;
        display: flex;
    }}
    .sd-cta {{
        background: var(--sd-surface);
        border: 1px solid var(--sd-border);
        border-radius: 8px;
        padding: 1.25rem 1.35rem 1rem;
        width: 100%;
        display: flex;
        flex-direction: column;
        transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.2s ease;
        animation: sd-fade-up 0.55s ease both;
    }}
    .sd-cta:hover {{
        border-color: var(--sd-accent);
        box-shadow: 0 8px 28px rgba(26,43,52,0.08);
        transform: translateY(-2px);
    }}
    .sd-cta h3 {{
        font-family: "Fraunces", Georgia, serif !important;
        font-size: 1.15rem !important;
        margin: 0 0 0.45rem 0 !important;
        color: var(--sd-text) !important;
        min-height: 2.6em;
        line-height: 1.3 !important;
    }}
    .sd-cta p {{
        margin: 0;
        color: var(--sd-muted);
        font-size: 0.92rem;
        line-height: 1.45;
        flex: 1 1 auto;
    }}

    .sd-brand-bar {{
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.5rem;
        animation: sd-fade-up 0.4s ease both;
    }}
    .sd-brand-bar img {{
        height: 64px;
        width: auto;
        object-fit: contain;
    }}
    .sd-brand-meta {{
        font-size: 0.85rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--sd-muted);
        font-weight: 600;
    }}

    .sd-hero {{
        margin-bottom: 1.75rem;
        animation: sd-fade-up 0.5s ease 0.05s both;
    }}
    .sd-hero h1 {{
        font-size: clamp(2.4rem, 5vw, 3.2rem) !important;
        font-weight: 700 !important;
        line-height: 1.08 !important;
        margin: 0 0 0.65rem 0 !important;
    }}
    .sd-hero .sd-tagline {{
        font-size: 1.15rem;
        color: var(--sd-text);
        font-weight: 500;
        margin: 0 0 0.55rem 0;
        max-width: 34em;
    }}
    .sd-hero .sd-support {{
        font-size: 0.98rem;
        color: var(--sd-muted);
        margin: 0;
        max-width: 38em;
        line-height: 1.5;
    }}

    .sd-authors {{
        margin-top: 1.75rem;
        padding-top: 1.35rem;
        border-top: 1px solid var(--sd-border);
        animation: sd-fade-up 0.55s ease 0.12s both;
    }}
    .sd-authors h2 {{
        font-size: 1.1rem !important;
        margin: 0 0 0.85rem 0 !important;
    }}
    .sd-author {{
        margin-bottom: 0.85rem;
    }}
    .sd-author .name {{
        font-family: "Fraunces", Georgia, serif;
        font-size: 1.02rem;
        font-weight: 600;
        color: var(--sd-text);
        margin-bottom: 0.15rem;
    }}
    .sd-author .role {{
        color: var(--sd-muted);
        font-size: 0.88rem;
        margin-bottom: 0.1rem;
    }}
    .sd-author a {{
        color: var(--sd-accent);
        text-decoration: none;
        font-weight: 500;
        font-size: 0.92rem;
    }}
    .sd-author a:hover {{
        text-decoration: underline;
    }}

    .sd-footer {{
        margin-top: 1.75rem;
        padding-top: 1rem;
        border-top: 1px solid var(--sd-border);
        font-size: 0.8rem;
        color: var(--sd-muted);
        line-height: 1.5;
        max-width: 42em;
        animation: sd-fade-up 0.6s ease 0.18s both;
    }}

    @keyframes sd-fade-up {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    {layout_rules}
    </style>
    """


def inject_css(home: bool = False) -> str:
    """Inyecta CSS en la app Streamlit. Retorna el bloque (útil para tests)."""
    block = css_block(home=home)
    st.markdown(block, unsafe_allow_html=True)
    return block
