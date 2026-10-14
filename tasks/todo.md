# TODO — Update Generación de EPW ← Solar Decomp v1.1.0

Fuente de verdad del detalle: [`tasks/plan.md`](plan.md).  
Marcar casillas al completar. No implementar hasta aprobación humana del plan.

## Estado

- [x] Plan revisado / aprobado
- [x] Decisiones: UI igual; ciencia v1.1.0 en ambos modos; cambios visuales mínimos

## Checkpoint 0 — Baseline

- [ ] `pytest tests/` verde en HEAD actual (29 tests)
- [ ] Anotar baseline DIRINT legacy vs Perez (para comparar después)

## Fase A — Núcleo científico

### T1 — Deps + geometría + DIRINT Perez
- [ ] Añadir `pvlib>=0.10`, `xlrd>=2.0.1` a `requirements.txt`
- [ ] Portar `config.py` (`MIN_COSZ_DEFAULT`)
- [ ] Portar `solar_geometry.py` (Spencer/Cooper + dew point + presión por altitud)
- [ ] Portar `decomposition.py` (Perez, legacy, Reindl-2, `use_dew_point`)
- [ ] Portar `tests/test_dirint_perez1992.py`
- [ ] **AC:** test DIRINT Perez PASS; columnas Reindl-2 presentes

### T2 — Presión + preprocessor
- [ ] Portar `preprocessor.py` (`pressure_to_kpa`, `dew_point_C`, `altitude_m`)
- [ ] Migrar o shimear `normalize_pressure_to_kpa` → no romper fill/tests locales
- [ ] Integrar tests presión upstream + adaptar `tests/test_pressure_units.py`
- [ ] **AC:** kPa/hPa/Pa coherentes; plantilla kPa intacta
- [ ] **Checkpoint A:** `test_pipeline.py` + pytest presión/DIRINT verdes

## Fase B — I/O descompositor

### T3 — io_handler v1.1.0
- [ ] Portar `io_handler.py` (EPW input, RH/Td, plantillas, comentarios `#`)
- [ ] Evitar colisión de imports con `epw_io.read_epw`
- [ ] Portar `test_epw_loader`, `test_loader_templates`, `test_dewpoint_humidity`
- [ ] **AC:** esos tests PASS + `tests/test_epw_io.py` PASS

### T4 — reference + reporter
- [ ] Añadir `reference.py`
- [ ] Portar `reporter.py` (columnas nuevas / templates decomp)
- [ ] Portar `test_reference_consistency.py`
- [ ] **AC:** consistency_table OK; exports no rompen modo EPW
- [ ] **Checkpoint B:** EPW sintético → decomp → tabla consistencia

## Fase C — UI Descomposición

### T5 — app_solar modo decomp
- [ ] Upload EPW + autofill sitio
- [ ] UI: tres modelos, Perez 1992, `use_dew_point`, `min_cosz`, preserve en EPW off
- [ ] Mostrar consistency table
- [ ] Preservar Home / router / branding
- [ ] **AC:** smoke manual CSV + EPW
- [ ] **Checkpoint C:** modo Descomposición E2E

## Fase D — Generación EPW

### T6 — fill_components + ui_epw
- [ ] Adaptar `LoadedData` / `run_decomposition` en `fill_components.py`
- [ ] Preservar override presión kPa de plantilla
- [ ] Cablear elevación/altitude si aplica
- [ ] Defaults seguros (`use_dew_point=False`)
- [ ] **AC:** fill + integration + merge + presión PASS
- [ ] **Checkpoint D:** ambos modos verdes

## Fase E — Cierre

### T7 — Docs / assets
- [ ] README + LEEME actualizados
- [ ] Distinguir `io_handler.read_epw` vs `epw_io.read_epw`
- [ ] Plantillas decomp opcionales sin pisar plantilla EPW
- [ ] CHANGELOG / versión (según decisión humana)

### T8 — Suite final
- [ ] `pytest tests/ -v` todo verde
- [ ] `test_pipeline.py` OK
- [ ] Smoke UI Home → Descomposición + Generación EPW
- [ ] **Done** según checklist de `plan.md` §8

## Fuera de alcance (no marcar como bloqueante)

- [ ] Deploy Streamlit Cloud
- [ ] Assets paper / 41 ciudades
- [ ] Unificar APIs EPW en un solo módulo
