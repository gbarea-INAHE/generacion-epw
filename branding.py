"""
branding.py — Identidad institucional, autores y textos de portada.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS_DIR = ROOT / "assets"
LOGO_PATH = ASSETS_DIR / "inahe_logo.jpg"

PRODUCT_NAME = "Generación de EPW"
INSTITUTION = "INAHE · CONICET"
INSTITUTION_FULL = "Instituto de Ambientes de Montaña y Regiones Áridas — CONICET"

TAGLINE = "Descomposición solar e incorporación de datos medidos en archivos climáticos EPW"

SUPPORTING = (
    "Herramienta científico-técnica para estimar DNI y DHI a partir de GHI "
    "e incorporar series medidas en archivos climáticos EnergyPlus (EPW)."
)

DISCLAIMER = (
    "Esta herramienta se encuentra en desarrollo y validación. Los resultados deben "
    "interpretarse como apoyo técnico-científico preliminar y no reemplazan la evaluación "
    "profesional específica de cada caso. El usuario es responsable de verificar la calidad "
    "de los datos cargados e interpretar los resultados en su contexto."
)


@dataclass(frozen=True)
class Author:
    name: str
    title: str
    email: str
    affiliation: str = "INAHE-CONICET"


AUTHORS: tuple[Author, ...] = (
    Author(
        name="Dr. Arq. Gustavo Barea Paci",
        title="INAHE - CONICET",
        email="gbarea@mendoza-conicet.gob.ar",
    ),
    Author(
        name="Dra. Arq. Carolina Ganem",
        title="INAHE - CONICET",
        email="cganem@mendoza-conicet.gob.ar",
    ),
)

# Accesos de la portada
MODE_DECOMP = "decomp"
MODE_EPW = "epw"
MODE_HOME = "home"

CTA_DECOMP_TITLE = "Descomposición GHI → DNI + DHI"
CTA_DECOMP_DESC = (
    "Cargá una serie de irradiancia global y obtené componentes directa y difusa "
    "con DIRINT o Erbs, control de calidad y exportación."
)
CTA_DECOMP_BUTTON = "Abrir descomposición"

CTA_EPW_TITLE = "Generación de EPW"
CTA_EPW_DESC = (
    "Subí una plantilla de datos medidos y un EPW base: completamos DNI/DHI "
    "faltantes e incorporamos tus medidas en un EPW listo para simulación."
)
CTA_EPW_BUTTON = "Abrir generación de EPW"


def epw_attribution_comments() -> tuple[str, str]:
    """
    Textos para COMMENTS 1 / COMMENTS 2 del EPW generado.
    Sin comas internas (el formato EPW usa la primera coma como separador).
    """
    authors = " y ".join(a.name for a in AUTHORS)
    emails = " | ".join(a.email for a in AUTHORS)
    c1 = (
        f"COMMENTS 1,Generado con {PRODUCT_NAME} (INAHE-CONICET) por {authors}"
    )
    c2 = (
        f"COMMENTS 2,"
        f"Descomposicion solar e incorporacion de datos medidos. Contacto: {emails}"
    )
    return c1, c2


def logo_exists() -> bool:
    return LOGO_PATH.is_file()
