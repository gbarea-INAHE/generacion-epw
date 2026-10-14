"""
app_solar.py — Streamlit UI Solar Decomp (INAHE-CONICET).

Portada institucional → modos Descomposición | EPW desde medidos.

Ejecutar:
  streamlit run app_solar.py
"""
from __future__ import annotations

import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from branding import MODE_DECOMP, MODE_EPW, MODE_HOME, PRODUCT_NAME
from decomposition import run_decomposition
from io_handler import load_file, summarize_loaded
from preprocessor import aggregate_to_hourly
from reference import consistency_table, hourly_reference
from reporter import (
    build_quality_report,
    export_csv,
    export_excel,
    generate_template_csv,
    generate_template_excel,
    report_to_json_str,
)
from theme import PLOTLY_COLORS, inject_css
from ui_epw import render_epw_mode
from ui_home import render_back_to_home, render_home
from validator import validate

_TEMPLATE_PATH = Path(__file__).resolve().parent / "assets" / "plantilla_datos_v2.xlsx"

# ─────────────────────────────────────────────────────────────────────────────
# Configuración de página
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=f"{PRODUCT_NAME} — INAHE-CONICET",
    page_icon="🔆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Estado de sesión
# ─────────────────────────────────────────────────────────────────────────────
for key in ["loaded", "df_hourly", "df_result", "report", "site_info", "ref_table"]:
    if key not in st.session_state:
        st.session_state[key] = None

if "app_page" not in st.session_state:
    st.session_state.app_page = MODE_HOME

# Router
if st.session_state.app_page == MODE_HOME:
    render_home()
    st.stop()

if st.session_state.app_page == MODE_EPW:
    render_epw_mode()
    st.stop()

# ── Modo descomposición ──────────────────────────────────────────────────────
inject_css(home=False)

COLORS = PLOTLY_COLORS


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de gráficos
# ─────────────────────────────────────────────────────────────────────────────


def _ts_series(df: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(df["timestamp_start"])


def fig_irradiance_timeseries(df: pd.DataFrame) -> go.Figure:
    ts = _ts_series(df)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ts, y=df["GHI_h"],     name="GHI",        line=dict(color=COLORS["GHI"],  width=0.9)))
    fig.add_trace(go.Scatter(x=ts, y=df["DNI_dirint"],name="DNI (DIRINT)",line=dict(color=COLORS["DNI_dirint"], width=0.9)))
    fig.add_trace(go.Scatter(x=ts, y=df["DHI_dirint"],name="DHI (DIRINT)",line=dict(color=COLORS["DHI_dirint"], width=0.9)))
    fig.update_layout(
        title="Serie temporal de irradiancia horaria",
        xaxis_title="Fecha",
        yaxis_title="W/m²",
        hovermode="x unified",
        height=380,
        margin=dict(t=50, b=40, l=60, r=20),
        legend=dict(orientation="h", y=1.08),
    )
    return fig


def fig_model_comparison(df: pd.DataFrame) -> go.Figure:
    """Scatter DNI_dirint vs DNI_erbs + identidad."""
    mask = df["DNI_dirint"].notna() & df["DNI_erbs"].notna()
    d = df[mask]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d["DNI_erbs"], y=d["DNI_dirint"],
        mode="markers",
        marker=dict(size=3, color=COLORS["DNI_dirint"], opacity=0.5),
        name="DNI: DIRINT vs Erbs",
    ))
    lim = max(float(d["DNI_erbs"].max()), float(d["DNI_dirint"].max()), 100)
    fig.add_trace(go.Scatter(
        x=[0, lim], y=[0, lim],
        mode="lines",
        line=dict(dash="dash", color="grey", width=1),
        name="1:1",
    ))
    fig.update_layout(
        title="DNI: DIRINT vs Erbs",
        xaxis_title="DNI Erbs [W/m²]",
        yaxis_title="DNI DIRINT [W/m²]",
        height=360,
        margin=dict(t=50, b=40, l=60, r=20),
    )
    return fig


def fig_kt_histogram(df: pd.DataFrame) -> go.Figure:
    kt = df.loc[(df["G0h"] > 0) & df["Kt"].notna(), "Kt"]
    fig = go.Figure(go.Histogram(
        x=kt, nbinsx=50,
        marker_color=COLORS["Kt"],
        opacity=0.8,
        name="Kt",
    ))
    fig.add_vline(x=1.0, line_dash="dash", line_color="red",
                  annotation_text="Cloud enh.", annotation_position="top right")
    fig.update_layout(
        title="Distribución del índice de claridad Kt (horas diurnas)",
        xaxis_title="Kt",
        yaxis_title="Frecuencia",
        height=320,
        margin=dict(t=50, b=40, l=60, r=20),
    )
    return fig


def fig_monthly_energy(df: pd.DataFrame) -> go.Figure:
    df2 = df.copy()
    df2["month"] = pd.to_datetime(df2["timestamp_start"]).dt.month
    month_names = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

    grp = df2[df2["G0h"] > 0].groupby("month")
    months = sorted(grp.groups.keys())
    ghi_kwh  = [grp.get_group(m)["GHI_h"].sum() / 1000 for m in months]
    dni_kwh  = [grp.get_group(m)["DNI_dirint"].sum() / 1000 for m in months]
    dhi_kwh  = [grp.get_group(m)["DHI_dirint"].sum() / 1000 for m in months]
    xlabels  = [month_names[m - 1] for m in months]

    fig = go.Figure()
    fig.add_bar(x=xlabels, y=ghi_kwh,  name="GHI",         marker_color=COLORS["GHI"])
    fig.add_bar(x=xlabels, y=dni_kwh,  name="DNI (DIRINT)", marker_color=COLORS["DNI_dirint"])
    fig.add_bar(x=xlabels, y=dhi_kwh,  name="DHI (DIRINT)", marker_color=COLORS["DHI_dirint"])
    fig.update_layout(
        barmode="group",
        title="Energía mensual (horas diurnas)",
        xaxis_title="Mes",
        yaxis_title="kWh/m²",
        height=360,
        margin=dict(t=50, b=40, l=60, r=20),
        legend=dict(orientation="h", y=1.08),
    )
    return fig


def fig_quality_score(df: pd.DataFrame) -> go.Figure:
    ts = _ts_series(df)
    qs = df["quality_score"]
    fig = go.Figure(go.Scatter(
        x=ts, y=qs,
        mode="lines",
        line=dict(color=COLORS["score"], width=0.9),
        fill="tozeroy",
        fillcolor="rgba(6,214,160,0.15)",
        name="Quality Score",
    ))
    fig.update_layout(
        title="Quality Score horario (0–100)",
        xaxis_title="Fecha",
        yaxis_title="Score",
        yaxis=dict(range=[0, 105]),
        height=300,
        margin=dict(t=50, b=40, l=60, r=20),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"**{PRODUCT_NAME}**")
    st.caption("Descomposición GHI → DNI + DHI")
    render_back_to_home()
    st.divider()

    st.subheader("0 · Plantilla")
    col_tmpl_a, col_tmpl_b = st.columns(2)
    with col_tmpl_a:
        _tmpl_bytes = (
            _TEMPLATE_PATH.read_bytes()
            if _TEMPLATE_PATH.is_file()
            else generate_template_excel()
        )
        st.download_button(
            "Template Excel",
            data=_tmpl_bytes,
            file_name="plantilla_datos_v2.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with col_tmpl_b:
        st.download_button(
            "Template CSV",
            data=generate_template_csv(),
            file_name="solar_decomp_template.csv",
            mime="text/csv",
            use_container_width=True,
        )
    st.divider()

    # ── 1. Carga de archivo ───────────────────────────────────────────────────
    st.subheader("1 · Datos de entrada")
    uploaded = st.file_uploader(
        "CSV, Excel (.xlsx) o EPW",
        type=["csv", "xlsx", "xls", "epw"],
        help=(
            "CSV/Excel: timestamp + GHI (1/15/60 min). "
            "EPW: 1 registro/hora; GHI + meteo; DNI/DHI como referencia."
        ),
    )

    if uploaded is not None and st.session_state.loaded is None:
        with st.spinner("Cargando archivo…"):
            try:
                ld = load_file(uploaded)
                st.session_state.loaded = ld
                st.session_state.df_hourly = None
                st.session_state.df_result = None
                st.session_state.report = None
                st.session_state.ref_table = None
            except Exception as e:
                st.error(f"Error al cargar: {e}")
                st.session_state.loaded = None

    if st.button("Resetear datos", use_container_width=True):
        for k in ["loaded", "df_hourly", "df_result", "report", "site_info", "ref_table"]:
            st.session_state[k] = None
        st.rerun()

    # ── 2. Información del sitio ──────────────────────────────────────────────
    st.subheader("2 · Sitio")
    _ep = st.session_state.loaded.epw_meta if st.session_state.loaded is not None else None
    if _ep:
        st.caption(
            f"Sitio del EPW «{_ep['city']}» ({_ep['country']}). Revisá antes de ejecutar."
        )
    lat = st.number_input(
        "Latitud [°N]",
        value=(_ep["lat"] if _ep else -34.6),
        min_value=-90.0, max_value=90.0, step=0.01, format="%.4f",
    )
    lon = st.number_input(
        "Longitud [°E]",
        value=(_ep["lon"] if _ep else -58.4),
        min_value=-180.0, max_value=180.0, step=0.01, format="%.4f",
    )
    alt = st.number_input(
        "Altitud [m s.n.m.]",
        value=(min(max(_ep["elev"], 0.0), 5000.0) if _ep else 25.0),
        min_value=0.0, max_value=5000.0, step=10.0, format="%.0f",
        help="Para estimar presión si no hay columna de presión.",
    )
    tz = st.number_input(
        "Zona horaria [UTC+]",
        value=(_ep["tz"] if _ep else -3.0),
        min_value=-12.0, max_value=14.0, step=0.5, format="%.1f",
    )

    # ── 3. Parámetros del modelo ──────────────────────────────────────────────
    st.subheader("3 · Modelo")
    st.caption(
        "Se calculan DIRINT (Perez 1992), Erbs y Reindl-2. "
        "Las columnas DNI/DHI finales usan el modelo primario."
    )
    primary_model = st.selectbox(
        "Modelo primario",
        options=["DIRINT", "Erbs", "Reindl-2"],
        index=0,
        help="DIRINT = Perez et al. 1992 vía pvlib (default).",
    )
    min_cosz = st.slider(
        "Umbral min cos(Z)",
        min_value=0.01, max_value=0.20, value=0.08, step=0.01,
        help="Horas con cos(Z) menor se descartan (~0.08 ≈ 85°).",
    )
    _is_epw = st.session_state.loaded is not None and st.session_state.loaded.is_epw
    preserve_existing = st.checkbox(
        "No recalcular filas con DNI/DHI existentes",
        value=not _is_epw,
        help="En EPW desactivado por defecto: DNI/DHI del archivo son referencia.",
    )
    _ld_td = st.session_state.loaded
    _td_possible = _ld_td is not None and bool(
        _ld_td.dewpoint_col or (_ld_td.humidity_col and _ld_td.temp_col)
    )
    use_dew_point = st.checkbox(
        "Usar humedad / punto de rocío en el DIRINT",
        value=False,
        disabled=not _td_possible,
        help="Opcional. Por defecto DIRINT usa el bin de agua precipitable desconocida.",
    )

    st.divider()

    run_btn = st.button(
        "Ejecutar descomposición",
        type="primary",
        use_container_width=True,
        disabled=(st.session_state.loaded is None),
    )

# ─────────────────────────────────────────────────────────────────────────────
# LÓGICA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

if run_btn and st.session_state.loaded is not None:
    ld = st.session_state.loaded
    with st.spinner("Preprocesando y calculando geometría solar…"):
        try:
            df_hourly = aggregate_to_hourly(
                ld, lat_deg=lat, lon_deg=lon, tz_hr=tz, altitude_m=alt,
            )
            st.session_state.df_hourly = df_hourly
        except Exception as e:
            st.error(f"Error en preprocesamiento: {e}")
            st.error(traceback.format_exc())
            st.stop()

    with st.spinner("Ejecutando modelos DIRINT + Erbs + Reindl-2…"):
        try:
            df_dec = run_decomposition(
                df_hourly,
                primary=primary_model,
                min_cosz=min_cosz,
                use_dew_point=use_dew_point,
            )
        except Exception as e:
            st.error(f"Error en descomposición: {e}")
            st.error(traceback.format_exc())
            st.stop()

    ref_table = None
    if ld.dni_col or ld.dhi_col:
        try:
            _r_dni, _r_dhi = hourly_reference(ld, df_dec["timestamp_start"])
            ref_table = consistency_table(df_dec, _r_dni, _r_dhi)
        except Exception as e:
            st.warning(f"No se pudo calcular la consistencia con DNI/DHI del archivo: {e}")
    st.session_state.ref_table = ref_table

    if preserve_existing and ld.dni_col and ld.dhi_col:
        try:
            _grp_dni = ld.df.groupby(ld.df["_timestamp"].dt.floor("h"))[ld.dni_col].mean()
            _grp_dhi = ld.df.groupby(ld.df["_timestamp"].dt.floor("h"))[ld.dhi_col].mean()
            _orig_dni = pd.to_numeric(_grp_dni, errors="coerce").reindex(df_dec["timestamp_start"]).values
            _orig_dhi = pd.to_numeric(_grp_dhi, errors="coerce").reindex(df_dec["timestamp_start"]).values
            _has_dni = ~np.isnan(_orig_dni)
            _has_dhi = ~np.isnan(_orig_dhi)
            if _has_dni.any():
                df_dec.loc[_has_dni, "DNI"] = _orig_dni[_has_dni]
                df_dec.loc[_has_dni, "DNI_dirint"] = _orig_dni[_has_dni]
                df_dec.loc[_has_dni, "model_primary"] = "original"
            if _has_dhi.any():
                df_dec.loc[_has_dhi, "DHI"] = _orig_dhi[_has_dhi]
                df_dec.loc[_has_dhi, "DHI_dirint"] = _orig_dhi[_has_dhi]
        except Exception:
            pass

    with st.spinner("Validando y generando reporte…"):
        try:
            df_val = validate(df_dec)
            site_info = {
                "filename": ld.df.attrs.get("filename", "archivo_cargado"),
                "lat_deg": lat,
                "lon_deg": lon,
                "alt_m": alt,
                "tz_hr": tz,
                "resolution": ld.resolution_label,
                "min_cosz": min_cosz,
            }
            report = build_quality_report(df_val, site_info, primary_model)
            st.session_state.df_result = df_val
            st.session_state.report = report
            st.session_state.site_info = site_info
        except Exception as e:
            st.error(f"Error en validación: {e}")
            st.error(traceback.format_exc())
            st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# PANEL PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

if st.session_state.loaded is None:
    st.markdown("## Descomposición GHI → DNI + DHI")
    st.info(
        "Cargá un archivo CSV, Excel o EPW en el panel lateral para comenzar.\n\n"
        "**Columnas mínimas:** timestamp + GHI [W/m²].\n\n"
        "**Opcionales:** DNI, DHI (referencia), temperatura [°C], presión [kPa/hPa/Pa], "
        "humedad relativa [%] o punto de rocío [°C].\n\n"
        "**Resoluciones:** 1-min · 15-min · 60-min (EPW: horario)."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Modelos")
        st.markdown("""
**DIRINT** (Perez et al., 1992, vía pvlib)
- Kt', cenit, ΔKt' y agua precipitable
- Modelo primario por defecto

**Erbs** (Erbs et al., 1982)
- Polinomio Kd(Kt) por tramos
- Sin requerir T/P

**Reindl-2** (Reindl et al., 1990)
- Incorpora elevación solar sin(α)
        """)
    with col2:
        st.markdown("### Flujo")
        st.markdown("""
1. **Carga** — columnas y resolución (CSV/Excel/EPW)
2. **Preproceso** — agregación + geometría (Spencer/Cooper)
3. **Descomposición** — DIRINT + Erbs + Reindl-2
4. **Validación** — quality score
5. **Exportación** — CSV / Excel / JSON
        """)

elif st.session_state.df_result is None:
    # ── Archivo cargado, pendiente de ejecutar ────────────────────────────────
    ld = st.session_state.loaded
    summ = summarize_loaded(ld)

    st.markdown("## Archivo cargado — listo para procesar")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Filas totales",     f"{summ['n_rows']:,}")
    c2.metric("Resolución",        summ['resolution'])
    c3.metric("GHI máx [W/m²]",    f"{summ['ghi_max']:.1f}")
    c4.metric("Datos faltantes",   f"{summ['ghi_nan_pct']:.1f}%")

    st.markdown(f"**Inicio:** {summ['start']} &nbsp;|&nbsp; **Fin:** {summ['end']}")
    st.markdown(f"**Columna GHI:** `{summ['ghi_col']}`")

    detected_opt = []
    if summ["has_dni"]:      detected_opt.append("DNI (referencia)")
    if summ["has_dhi"]:      detected_opt.append("DHI (referencia)")
    if summ["has_temp"]:     detected_opt.append("Temperatura")
    if summ["has_pressure"]: detected_opt.append("Presión")
    if summ.get("has_dewpoint"):
        detected_opt.append("Punto de rocío (opcional en DIRINT)")
    elif summ.get("has_humidity"):
        detected_opt.append("Humedad relativa (→ punto de rocío; opcional en DIRINT)")
    if detected_opt:
        st.success("Columnas opcionales detectadas: " + ", ".join(detected_opt))

    if summ["warnings"]:
        for w in summ["warnings"]:
            st.warning(w)

    st.info("Configurá latitud, longitud y zona horaria en el panel lateral, luego ejecutá la descomposición.")

else:
    # ── RESULTADOS ────────────────────────────────────────────────────────────
    df   = st.session_state.df_result
    rep  = st.session_state.report
    s    = rep["summary"]

    st.markdown(f"## Resultados — modelo primario: **{rep['metadata']['primary_model']}**")

    # ── Métricas resumen ──────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Horas diurnas válidas",  f"{s['n_daytime_hours']:,}")
    c2.metric("GHI acum. [kWh/m²]",     f"{s['ghi_total_Wh_m2']/1000:.1f}")
    c3.metric("DNI acum. [kWh/m²]",     f"{s['dni_total_Wh_m2']/1000:.1f}")
    c4.metric("DHI acum. [kWh/m²]",     f"{s['dhi_total_Wh_m2']/1000:.1f}")
    c5.metric("Quality score (media)",   f"{s['quality_score_mean']:.1f}")

    c6, c7, c8, c9 = st.columns(4)
    c6.metric("Kt medio (diurno)",       f"{s['kt_mean']:.3f}")
    c7.metric("Kt máx",                  f"{s['kt_max']:.3f}")
    c8.metric("Horas inválidas",         f"{s['n_invalid_hours']:,}")
    flags = rep["flags"]
    n_enh = flags.get("flag_kt_cloud_enh", {}).get("count", 0)
    c9.metric("Cloud enhancement",       f"{n_enh} h")

    # ── Advertencias de flags ─────────────────────────────────────────────────
    n_unphy = flags.get("flag_kt_unphysical", {}).get("count", 0)
    if n_unphy > 0:
        st.warning(f"{n_unphy} horas con Kt > 1.05 (probable error de sensor).")
    if s["quality_score_min"] < 50:
        st.warning("Algunas horas tienen quality score < 50. Revisar reporte de flags.")

    ref_table = st.session_state.get("ref_table")
    if ref_table is not None and not getattr(ref_table, "empty", True):
        st.subheader("Consistencia con DNI/DHI del archivo")
        st.caption(
            "Comparación modelo vs columnas DNI/DHI del archivo (no es exactitud "
            "salvo que esas columnas sean mediciones)."
        )
        st.dataframe(ref_table, use_container_width=True, hide_index=True)

    st.divider()

    # ── Gráficos ──────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(["Serie temporal", "Energía mensual", "Comparación modelos", "Calidad"])

    with tab1:
        st.plotly_chart(fig_irradiance_timeseries(df), use_container_width=True)
        st.plotly_chart(fig_kt_histogram(df), use_container_width=True)

    with tab2:
        st.plotly_chart(fig_monthly_energy(df), use_container_width=True)

        # Tabla mensual
        monthly = rep.get("monthly_stats", {})
        if monthly:
            month_names = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
            rows = []
            for m, stats in sorted(monthly.items()):
                rows.append({
                    "Mes":            month_names[int(m) - 1],
                    "GHI [kWh/m²]":  stats["GHI_sum_kWh_m2"],
                    "DNI [kWh/m²]":  stats["DNI_sum_kWh_m2"],
                    "DHI [kWh/m²]":  stats["DHI_sum_kWh_m2"],
                    "Kt medio":       stats["Kt_mean"],
                    "Quality (med)":  stats["quality_mean"],
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with tab3:
        mc = rep.get("model_comparison", {})
        if mc:
            col_d, col_e = st.columns(2)
            col_d.markdown("**DNI**")
            col_d.metric("DIRINT medio [W/m²]",  f"{mc['DNI']['DIRINT_mean']:.1f}")
            col_d.metric("Erbs medio [W/m²]",    f"{mc['DNI']['Erbs_mean']:.1f}")
            col_d.metric("RMSE [W/m²]",           f"{mc['DNI']['RMSE_W_m2']:.1f}")
            col_d.metric("Diferencia [%]",        f"{mc['DNI']['diff_pct']:.1f}")

            col_e.markdown("**DHI**")
            col_e.metric("DIRINT medio [W/m²]",  f"{mc['DHI']['DIRINT_mean']:.1f}")
            col_e.metric("Erbs medio [W/m²]",    f"{mc['DHI']['Erbs_mean']:.1f}")
            col_e.metric("RMSE [W/m²]",           f"{mc['DHI']['RMSE_W_m2']:.1f}")
            col_e.metric("Diferencia [%]",        f"{mc['DHI']['diff_pct']:.1f}")

        st.plotly_chart(fig_model_comparison(df), use_container_width=True)

        st.markdown(
            "**Modelos**\n\n"
            "- **DIRINT** (Perez 1992): Kt', cenit, ΔKt' y agua precipitable.\n"
            "- **Erbs**: polinomio Kd(Kt); no requiere T/P ni humedad.\n"
            "- **Reindl-2**: incorpora sin(α). Los tres se exportan en el CSV/Excel."
        )

    with tab4:
        st.plotly_chart(fig_quality_score(df), use_container_width=True)

        # Tabla de flags
        flag_rows = []
        for fname, fdata in flags.items():
            flag_rows.append({
                "Flag":    fname,
                "Horas":   fdata["count"],
                "% horas": f"{fdata['pct']:.1f}%",
            })
        st.dataframe(pd.DataFrame(flag_rows), use_container_width=True, hide_index=True)

        # Distribución quality score
        qd = rep.get("quality_distribution", {})
        if qd:
            st.markdown("**Distribución del quality score**")
            qd_df = pd.DataFrame(
                [{"Rango": k, "Horas": v} for k, v in qd.items()]
            )
            st.dataframe(qd_df, use_container_width=True, hide_index=True)

    st.divider()

    # ── Exportar ──────────────────────────────────────────────────────────────
    st.subheader("Exportar resultados")
    col_exp1, col_exp2, col_exp3 = st.columns(3)

    with col_exp1:
        csv_bytes = export_csv(df, minimal=False)
        st.download_button(
            "CSV completo",
            data=csv_bytes,
            file_name="solar_decomp_resultados.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col_exp2:
        xlsx_bytes = export_excel(df, rep, minimal=False)
        st.download_button(
            "Excel (datos + reporte)",
            data=xlsx_bytes,
            file_name="solar_decomp_resultados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with col_exp3:
        json_str = report_to_json_str(rep)
        st.download_button(
            "Reporte JSON",
            data=json_str,
            file_name="solar_decomp_reporte.json",
            mime="application/json",
            use_container_width=True,
        )

    # ── Tabla de datos (expandible) ───────────────────────────────────────────
    with st.expander("Ver tabla de datos (primeras 96 filas)"):
        preview_cols = [
            "timestamp_start", "GHI_h", "DNI_dirint", "DHI_dirint",
            "DNI_erbs", "DHI_erbs", "DNI_reindl2", "DHI_reindl2",
            "Kt", "zenith_deg", "quality_score",
        ]
        show_cols = [c for c in preview_cols if c in df.columns]
        st.dataframe(
            df[show_cols].head(96).style.format(
                {c: "{:.2f}" for c in show_cols if c != "timestamp_start"},
                na_rep="—",
            ),
            use_container_width=True,
        )
