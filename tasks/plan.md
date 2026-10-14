# Plan: actualizar Generación de EPW con Solar Decomp v1.1.0

**Fecha:** 2026-10-14  
**Fuente:** [gbarea-INAHE/solar_decomp](https://github.com/gbarea-INAHE/solar_decomp) @ `17ce7aa` (release/v1.1.0, mergeado hoy)  
**Destino:** este repo `generacion-epw` (superset: descomposición + generación EPW)  
**Estado:** plan para revisión humana — sin implementación aún

---

## 1. Contexto

`generacion-epw` nació a partir de Solar Decomp (modo descomposición) y añade un segundo modo: **Generación de EPW** (plantilla medidos + EPW base → EPW modificado).

Solar Decomp publicó **v1.1.0** con cambios científicos y de I/O importantes. Este repo aún está en la línea v1.0.x del núcleo de descomposición (más un fix local de presión kPa).

### Objetivo

Traer el núcleo de descomposición v1.1.0 **sin romper** el modo Generación de EPW ni los tests actuales de merge/plantilla.

### No-objetivo (fuera de alcance salvo pedirlo)

- Publicar paper / assets de validación de 41 ciudades
- Cambiar identidad de marca / portada institucional
- Reescribir `epw_io` / `epw_merge` (salvo adaptar llamadas al nuevo pipeline)
- Deploy a Streamlit Cloud (puede ser follow-up)

---

## 2. Delta principal (v1.0.x local → v1.1.0 upstream)

| Área | Este repo hoy | Upstream v1.1.0 | Impacto |
|------|---------------|-----------------|---------|
| DIRINT | Tabla propia (no Perez 1992) | Perez 1992 vía `pvlib.irradiance.dirint`; legacy en `dirint_series_v1` | **Alto** — cambia DNI/DHI |
| Modelos | DIRINT + Erbs | + **Reindl-2** | Medio — UI/export |
| Geometría | Yallop (código local) | Spencer / Cooper | **Alto** — base G0/cosZ |
| Presión | `normalize_pressure_to_kpa` (ya corregido parcialmente) | `pressure_to_kpa` + error si no es presión de superficie | Medio — renombrar/adaptar tests |
| Humedad / Td | Solo se propaga RH en fill EPW | Detección RH/Td; `dew_point_C`; opcional `use_dew_point` en DIRINT | Medio |
| Entrada EPW (decomp) | No | `io_handler.read_epw` + autofill sitio | Medio — **nombre choca** con `epw_io.read_epw` |
| Consistencia DNI/DHI | No | `reference.py` (RMSE/MBE/nRMSE/R²) | Medio — UI decomp |
| Deps | sin pvlib / xlrd | `pvlib>=0.10`, `xlrd>=2.0.1` | Bajo |
| Python | no declarado | ≥ 3.11 | Bajo (entorno ya 3.12) |

### Archivos a portar / reemplazar desde upstream

- Reemplazar (núcleo): `decomposition.py`, `solar_geometry.py`, `preprocessor.py`, `io_handler.py`, `reporter.py`, `config.py`
- Nuevo: `reference.py`
- Deps: `requirements.txt` (+ pytest local se mantiene)
- Tests upstream a integrar bajo `tests/`: `test_dirint_perez1992`, `test_dewpoint_humidity`, `test_epw_loader`, `test_loader_templates`, `test_reference_consistency`, `test_pressure_units` (upstream), actualizar `test_pipeline.py`
- UI modo descomposición: adaptar `app_solar.py` (no copiar ciego: este repo tiene router Home / Decomp / EPW)

### Archivos a conservar (específicos de generación EPW)

- `branding.py`, `theme.py`, `ui_home.py`, `ui_epw.py`
- `epw_io.py`, `epw_merge.py`, `fill_components.py`, `measured_template.py`
- `templates/plantilla_medidos_epw.xlsx`, `generate_test_data.py`
- Tests: `tests/test_epw_*`, `test_fill_components`, `test_measured_template`, `test_branding`, `test_integration_epw`

### Riesgo de naming

- `epw_io.read_epw` → lee/escribe EPW para **merge/generación** (API propia `EpwFile`)
- `io_handler.read_epw` (nuevo) → carga EPW como **entrada del descompositor**

**Regla:** no unificar APIs en esta actualización. Mantener ambos; imports explícitos (`from epw_io import read_epw as read_epw_file` o alias en UI). Documentar en README.

---

## 3. Grafo de dependencias

```text
requirements (pvlib, xlrd)
    └── config (MIN_COSZ_DEFAULT)
          └── solar_geometry (Spencer/Cooper, dew_point_from_rh, pressure_from_altitude)
                └── io_handler (LoadedData + humidity/dew/epw_meta + read_epw + plantillas)
                      └── preprocessor (pressure_to_kpa, dew_point_C, altitude)
                            └── decomposition (Perez DIRINT, Reindl-2, legacy, use_dew_point)
                                  ├── reference (consistency_table)
                                  ├── reporter (columnas nuevas + templates)
                                  ├── app_solar modo Descomposición (UI)
                                  └── fill_components → ui_epw (modo Generación EPW)
```

`validator.py` no cambia en upstream (diff 0).  
`epw_merge` / `measured_template` no dependen del modelo DIRINT salvo vía `fill_components`.

---

## 4. Slices verticales (una ruta completa por tarea)

Cada tarea entrega un camino usable + verificación. No cortar por capas horizontales (“primero todos los módulos, después UI”).

### Checkpoint 0 — Baseline (antes de tocar código)

**Criterio:** baseline documentado.  
**Verificar:**

```bash
python3 -m pytest tests/ -v          # hoy: 29 passed
python3 test_pipeline.py             # smoke local
```

Registrar que DNI DIRINT actual ≠ Perez 1992 (esperado).

---

### Fase A — Núcleo científico (sin UI)

#### T1 — Dependencias + config + geometría + DIRINT Perez

**Entrega:** pipeline `load → aggregate → run_decomposition` produce DIRINT Perez + Erbs + Reindl-2.  
**Cambios:** `requirements.txt`, `config.py`, `solar_geometry.py`, `decomposition.py` (port upstream).  
**Compat:** mantener `run_decomposition(df, primary=...)` con defaults; nuevos kwargs opcionales (`min_cosz`, `legacy_dirint`, `use_dew_point`).  
**Aceptación:**

- `pvlib` importable
- `test_dirint_perez1992` (portado) PASS
- `run_decomposition(..., legacy_dirint=True)` reproduce comportamiento tipo v1.0 para regresión opcional
- Erbs sigue disponible; aparecen columnas `DNI_reindl2` / `DHI_reindl2`

**Verificar:**

```bash
pip install -r requirements.txt
python3 -m pytest tests/test_dirint_perez1992.py -v
```

#### T2 — Presión + preprocessor (API nueva)

**Entrega:** `pressure_to_kpa` + `aggregate_to_hourly` con Td/RH y presión estricta.  
**Cambios:** `preprocessor.py`; shim o migración de `normalize_pressure_to_kpa` usada por `tests/test_pressure_units.py` y fill path.  
**Aceptación:**

- Tests presión upstream PASS
- Tests locales de presión actualizados (o shim que preserve `normalize_pressure_to_kpa` como wrapper)
- kPa de plantilla (~97) no se interpreta como hPa

**Verificar:**

```bash
python3 -m pytest tests/test_pressure_units.py -v
```

**Checkpoint A:** `test_pipeline.py` + tests DIRINT/presión verdes. Sin UI todavía.

---

### Fase B — I/O del descompositor

#### T3 — `io_handler` v1.1.0 (CSV/Excel/EPW + RH/Td)

**Entrega:** `load_file` acepta EPW y detecta humedad/punto de rocío; `LoadedData` con `humidity_col`, `dewpoint_col`, `epw_meta`.  
**Cuidado:** no romper imports de `epw_io.read_epw` en `ui_epw.py` / tests EPW.  
**Aceptación:**

- `tests/test_epw_loader.py` PASS
- `tests/test_loader_templates.py` PASS
- `tests/test_dewpoint_humidity.py` PASS
- Tests existentes `tests/test_epw_io.py` siguen PASS (API de generación intacta)

**Verificar:**

```bash
python3 -m pytest tests/test_epw_loader.py tests/test_loader_templates.py tests/test_dewpoint_humidity.py tests/test_epw_io.py -v
```

#### T4 — `reference.py` + `reporter.py`

**Entrega:** tabla de consistencia vs DNI/DHI del archivo; exports con columnas nuevas (`dirint_version`, Reindl-2, dew point, etc.).  
**Aceptación:**

- `tests/test_reference_consistency.py` PASS
- Export CSV/Excel/JSON no rompe columnas usadas por modo EPW

**Checkpoint B:** carga EPW sintético → descompone → consistency_table sin error.

---

### Fase C — UI modo Descomposición

#### T5 — Adaptar `app_solar.py` (modo decomp) al v1.1.0

**Entrega:** en el modo Descomposición (preservando Home + router):

- Upload CSV / Excel / EPW
- Autofill lat/lon/tz/elev desde EPW
- Checkbox `use_dew_point` (off por defecto; enable si hay datos)
- `min_cosz` / preserve_existing (off por defecto en EPW)
- Textos Perez 1992 / tres modelos / sin “validación Córdoba”
- Tabla de consistencia si el archivo trae DNI/DHI
- Gráficos/export incluyen Reindl-2 donde aplique

**No copiar** la app monolítica upstream: integrar en el flujo actual con `theme`/`branding`.  
**Aceptación (manual):**

1. Abrir Home → Descomposición
2. Subir `test_data_15min.csv` → resultados + score
3. Subir EPW sintético o de prueba → sitio autofill + consistency
4. Toggle dew point solo habilitado con RH/Td

**Verificar:** smoke Streamlit + checklist manual.

**Checkpoint C:** modo Descomposición usable end-to-end con v1.1.0.

---

### Fase D — Modo Generación de EPW (compatibilidad)

#### T6 — Adaptar `fill_components.py` al nuevo pipeline

**Entrega:** generación EPW sigue completando DNI/DHI faltantes con el nuevo DIRINT.  
**Cambios tipicos:**

- Pasar `humidity_col` / `dewpoint_col` en `LoadedData` si la plantilla trae RH / Dew Point
- Decidir defaults: `use_dew_point=False` (alineado a upstream); opcional checkbox en `ui_epw` (fase posterior si se pide)
- Presión plantilla en kPa: mantener override actual que fija `pressure_kPa` desde la plantilla
- `aggregate_to_hourly` ahora acepta `altitude_m` — cablear elevación del EPW base si está disponible en UI

**Aceptación:**

- `tests/test_fill_components.py` PASS
- `tests/test_integration_epw.py` PASS
- `tests/test_epw_merge.py` PASS
- Regresión presión: `test_fill_keeps_plantilla_pressure_as_kpa` PASS
- EPW generado sobrescribe solo horas con datos (comportamiento actual)

**Verificar:**

```bash
python3 -m pytest tests/test_fill_components.py tests/test_integration_epw.py tests/test_epw_merge.py tests/test_pressure_units.py -v
```

**Checkpoint D:** ambos modos verdes en tests + smoke UI Generación EPW con plantilla.

---

### Fase E — Docs, assets, cierre

#### T7 — Documentación y plantillas

**Entrega:**

- README: modelos v1.1.0, EPW como entrada del decomp, distinción de los dos “read EPW”, deps pvlib, Python ≥3.11
- `LEEME_PRIMERO.txt` breve
- Opcional: copiar/adaptar plantillas decomp upstream (`assets/plantilla_datos_v2.xlsx`) sin pisar `templates/plantilla_medidos_epw.xlsx`
- Nota de versión / CHANGELOG local (recomendado)

**Aceptación:** un usuario nuevo puede instalar y usar ambos modos siguiendo el README.

#### T8 — Suite completa + smoke final

**Aceptación:**

```bash
python3 -m pytest tests/ -v
python3 test_pipeline.py
# + scripts upstream portados si no viven bajo pytest
streamlit run app_solar.py   # Home → Decomp + EPW
```

Todos los tests PASS; checklist manual de ambos modos.

---

## 5. Orden recomendado y dependencias entre tareas

```text
T1 → T2 → Checkpoint A
         → T3 → T4 → Checkpoint B
                    → T5 → Checkpoint C
         → T6 (puede empezar en paralelo tras T2; cerrar tras T3) → Checkpoint D
                                                                  → T7 → T8
```

- **T6 depende de T1–T2** (API decomposition/preprocessor).  
- **T6 se beneficia de T3** (campos LoadedData RH/Td) pero puede aterrizar con shim mínimo.  
- **T5 depende de T3–T4** para EPW input + consistency UI.

---

## 6. Decisiones que requieren confirmación humana

1. **¿DIRINT Perez como default inmediato?** (recomendado: sí, con `legacy_dirint` oculto o solo vía flag para reproducibilidad).  
2. **¿Exponer Reindl-2 y dew-point en modo Generación EPW en esta misma release?** (recomendado: decomp sí; generación EPW con defaults seguros y UI mínima).  
3. **¿Versionar el producto** como `Generación de EPW 1.1.0` alineado a Solar Decomp, o versión propia (p. ej. 0.2.0)?  
4. **¿Portar plantillas decomp Excel/CSV** además de la plantilla EPW medidos?

---

## 7. Estrategia de implementación (cuando se apruebe)

1. Branch de trabajo (ya creada para este plan: `cursor/plan-update-solar-decomp-v110-fa2c`).  
2. Portar archivos núcleo por commit vertical (T1, T2, …), no un mega-commit.  
3. Tras cada checkpoint: `pytest` + commit/push.  
4. No reemplazar `app_solar.py` entero; merge funcional del modo decomp.  
5. Mantener separación `epw_io` (generación) vs `io_handler` (entrada decomp).

---

## 8. Criterio de “done” del upgrade

- [ ] Núcleo = Solar Decomp v1.1.0 (Perez DIRINT + Reindl-2 + presión + RH/Td + EPW input + reference)
- [ ] Modo Generación EPW sigue generando EPW parciales correctos
- [ ] Suite `tests/` ampliada con tests upstream + tests locales EPW, todo verde
- [ ] README actualizado
- [ ] Smoke UI de ambos modos

---

## 9. Referencias

- Upstream CHANGELOG: `/tmp/solar_decomp/CHANGELOG.md` (clon local de comparación) / [repo](https://github.com/gbarea-INAHE/solar_decomp)
- Commit release: `8cc568d` / merge `17ce7aa`
- App live de referencia: https://solar-decomp.streamlit.app
