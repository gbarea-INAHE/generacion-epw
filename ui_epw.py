"""
ui_epw.py — Modo Streamlit: plantilla medidos + EPW base → EPW modificado.
"""
from __future__ import annotations

import json
import traceback
from io import BytesIO
from pathlib import Path

import streamlit as st

from branding import (
    DECOMP_MODELS_BULLETS,
    PRODUCT_NAME,
    epw_attribution_comments,
)
from epw_io import read_epw, set_location_timezone, stamp_generation_comments
from epw_merge import build_modified_epw_bytes, merge_into_epw
from fill_components import fill_missing_solar
from measured_template import (
    generate_template_xlsx,
    load_measured_table,
    template_path_default,
)
from theme import inject_css
from ui_home import render_back_to_home


def render_epw_mode() -> None:
    """Renderiza sidebar + panel del flujo EPW desde medidos."""
    inject_css(home=False)

    for key in [
        "epw_fill", "epw_merged", "epw_report", "epw_bytes", "epw_name",
        "epw_site_source",
    ]:
        if key not in st.session_state:
            st.session_state[key] = None

    with st.sidebar:
        st.markdown(f"**{PRODUCT_NAME}**")
        st.caption("Datos medidos → EPW")
        render_back_to_home()
        st.divider()

        st.subheader("1 · Plantilla")
        tpl_bytes = generate_template_xlsx(n_hours=8760)
        st.download_button(
            "Descargar plantilla Excel",
            data=tpl_bytes,
            file_name="plantilla_medidos_epw.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            help="Completar Date/Time + GHI (y meteo/DNI/DHI opcionales).",
        )
        disk_tpl = template_path_default()
        if disk_tpl.exists():
            st.caption(f"Plantilla en disco: `{disk_tpl.name}`")

        measured_file = st.file_uploader(
            "Subir plantilla completada",
            type=["csv", "xlsx", "xls"],
            key="epw_measured_upload",
        )
        epw_file = st.file_uploader(
            "Subir EPW base",
            type=["epw"],
            key="epw_base_upload",
        )

        epw_loc = {}
        if epw_file is not None:
            try:
                epw_preview = read_epw(BytesIO(epw_file.getvalue()))
                epw_loc = epw_preview.location or {}
                if st.session_state.epw_site_source != epw_file.name and epw_loc:
                    if "latitude" in epw_loc:
                        st.session_state.epw_lat = float(epw_loc["latitude"])
                    if "longitude" in epw_loc:
                        st.session_state.epw_lon = float(epw_loc["longitude"])
                    if "tz" in epw_loc:
                        st.session_state.epw_tz = float(epw_loc["tz"])
                    if "elevation_m" in epw_loc:
                        st.session_state.epw_alt = float(epw_loc["elevation_m"])
                    st.session_state.epw_site_source = epw_file.name
            except Exception:
                pass

        st.subheader("2 · Sitio")
        if epw_loc:
            st.caption(
                f"Detectado en EPW: {epw_loc.get('city', '?')} | "
                f"lat={epw_loc.get('latitude', '?')} lon={epw_loc.get('longitude', '?')} "
                f"tz={epw_loc.get('tz', '?')} elev={epw_loc.get('elevation_m', '?')}"
            )

        lat = st.number_input(
            "Latitud [°N]",
            value=float(st.session_state.get("epw_lat", -34.6)),
            min_value=-90.0, max_value=90.0,
            step=0.01, format="%.4f", key="epw_lat",
        )
        lon = st.number_input(
            "Longitud [°E]",
            value=float(st.session_state.get("epw_lon", -58.4)),
            min_value=-180.0, max_value=180.0,
            step=0.01, format="%.4f", key="epw_lon",
        )
        alt = st.number_input(
            "Altitud [m s.n.m.]",
            value=float(st.session_state.get("epw_alt", 0.0)),
            min_value=0.0, max_value=5000.0,
            step=10.0, format="%.0f", key="epw_alt",
            help="Para estimar presión si la plantilla no trae presión medida.",
        )
        tz = st.number_input(
            "Zona horaria mediciones [UTC+]",
            value=float(st.session_state.get("epw_tz", -3.0)),
            min_value=-12.0, max_value=14.0,
            step=0.5, format="%.1f", key="epw_tz",
            help=(
                "Zona horaria REAL de tus timestamps medidos "
                "(Mendoza/Argentina hoy: UTC−3)."
            ),
        )
        sync_tz_header = st.checkbox(
            "Actualizar tz en cabecera LOCATION del EPW",
            value=True,
            key="epw_sync_tz",
        )
        st.caption(
            "Priorizá el reloj de tus mediciones (−3 en Argentina actual). "
            "El −4 de EPW históricos suele ser convención vieja."
        )

        st.subheader("3 · Modelos")
        st.info(
            "Al rellenar huecos se calculan los **3 modelos en paralelo**. "
            "El modelo primario define DNI/DHI finales cuando faltan en la plantilla.",
            icon="ℹ️",
        )
        st.markdown(DECOMP_MODELS_BULLETS)
        primary = st.selectbox(
            "Modelo primario (si falta DNI/DHI)",
            options=["DIRINT", "Erbs", "Reindl-2"],
            index=0,
            key="epw_primary",
            help=(
                "DIRINT = Perez et al. 1992 (pvlib). "
                "Si DIRINT no tiene vecinos horarios (horas aisladas), se usa Erbs/Reindl-2 como respaldo."
            ),
        )

        st.divider()
        run = st.button(
            "Generar EPW modificado",
            type="primary",
            use_container_width=True,
            disabled=(measured_file is None or epw_file is None),
        )
        if st.button("Resetear EPW", use_container_width=True, key="epw_reset"):
            for k in [
                "epw_fill", "epw_merged", "epw_report", "epw_bytes", "epw_name",
                "epw_site_source",
            ]:
                st.session_state[k] = None
            st.rerun()

    st.markdown(f"## {PRODUCT_NAME}")
    st.info(
        "1. Descargá la plantilla y completá tus medidas (parcial OK).\n"
        "2. Subí la plantilla + un EPW base.\n"
        "3. Completamos DNI/DHI faltantes e incorporamos GHI, DNI, DHI, "
        "Dry Bulb, Pressure y RH solo en horas con datos.\n"
        "4. Zona horaria: la de tus mediciones.\n"
        "5. El EPW de salida incluye en COMMENTS la atribución de esta herramienta."
    )

    if run and measured_file is not None and epw_file is not None:
        try:
            with st.spinner("Cargando plantilla…"):
                md = load_measured_table(measured_file, filename=measured_file.name)
            with st.spinner("Rellenando DNI/DHI faltantes…"):
                fill = fill_missing_solar(
                    md,
                    lat_deg=lat,
                    lon_deg=lon,
                    tz_hr=tz,
                    primary=primary,
                    altitude_m=alt,
                )
            with st.spinner("Leyendo EPW y mergeando…"):
                epw = read_epw(BytesIO(epw_file.getvalue()))
                epw_tz = epw.location.get("tz") if epw.location else None
                if (
                    epw_tz is not None
                    and abs(float(epw_tz) - float(tz)) > 1e-6
                ):
                    fill.warnings.append(
                        f"Tz del EPW base ({epw_tz}) distinto de tz de mediciones ({tz}). "
                        "Para descomposicion se uso el tz de mediciones."
                        + (
                            f" Cabecera LOCATION se actualizara a {tz}."
                            if sync_tz_header
                            else " Cabecera LOCATION se conserva."
                        )
                    )
                merged, report = merge_into_epw(epw, fill)
                if sync_tz_header:
                    merged = set_location_timezone(merged, tz)
                    report.warnings.append(
                        f"LOCATION timezone actualizado a {tz}."
                    )
                c1, c2 = epw_attribution_comments()
                merged = stamp_generation_comments(merged, c1, c2)
                report.warnings.append(
                    "Cabecera COMMENTS 1/2: atribucion de Generacion de EPW (INAHE-CONICET)."
                )
                epw_bytes = build_modified_epw_bytes(merged)

            base_name = Path(epw_file.name).stem
            st.session_state.epw_fill = fill
            st.session_state.epw_merged = merged
            st.session_state.epw_report = report
            st.session_state.epw_bytes = epw_bytes
            st.session_state.epw_name = f"{base_name}_modified.epw"
            st.success("EPW generado correctamente.")
        except Exception as e:
            st.error(f"Error: {e}")
            st.code(traceback.format_exc())

    if st.session_state.epw_report is None:
        return

    rep = st.session_state.epw_report
    fill = st.session_state.epw_fill

    st.markdown("### Resumen del merge")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Horas EPW", f"{rep.epw_hours_total:,}")
    c2.metric("Horas plantilla", f"{rep.measured_hours:,}")
    c3.metric("Horas matched", f"{rep.hours_matched:,}")
    c4.metric("Sin match", f"{rep.hours_unmatched_measured:,}")

    c5, c6, c7 = st.columns(3)
    c5.metric("GHI sobrescritos", rep.n_ghi_overwritten)
    c6.metric("DNI sobrescritos", rep.n_dni_overwritten)
    c7.metric("DHI sobrescritos", rep.n_dhi_overwritten)

    c8, c9, c10 = st.columns(3)
    c8.metric("Dry Bulb", rep.n_dry_bulb_overwritten)
    c9.metric("Pressure", rep.n_pressure_overwritten)
    c10.metric("RH", rep.n_rh_overwritten)

    c11, c12 = st.columns(2)
    c11.metric("DNI rellenados (modelo)", rep.n_dni_filled_by_model)
    c12.metric("DHI rellenados (modelo)", rep.n_dhi_filled_by_model)

    if rep.fields_touched:
        st.caption("Campos tocados: " + ", ".join(rep.fields_touched))

    for w in rep.warnings:
        st.warning(w)
    if fill and fill.warnings:
        for w in fill.warnings:
            st.warning(w)

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "Descargar EPW modificado",
            data=st.session_state.epw_bytes,
            file_name=st.session_state.epw_name or "modified.epw",
            mime="text/plain",
            type="primary",
            use_container_width=True,
        )
    with col_b:
        st.download_button(
            "Descargar reporte JSON",
            data=json.dumps(rep.to_dict(), indent=2, ensure_ascii=False),
            file_name="merge_report.json",
            mime="application/json",
            use_container_width=True,
        )
