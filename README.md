# Generación de EPW

Herramienta **INAHE-CONICET** para:

1. Descomponer **GHI → DNI + DHI** (motor **Solar Decomp v1.1.0**: DIRINT Perez 1992 / Erbs / Reindl-2)
2. Generar un **EPW modificado** a partir de datos medidos + EPW base (usa el mismo motor científico)

**Autores:** Dr. Arq. Gustavo Barea Paci · Dra. Arq. Carolina Ganem

Núcleo científico alineado a [solar_decomp](https://github.com/gbarea-INAHE/solar_decomp) v1.1.0. La plataforma visual (portada, branding, modo Generación EPW) se conserva.

## Ejecutar en tu PC

```bash
pip install -r requirements.txt
streamlit run app_solar.py
```

Requisito: **Python 3.11+**. En Windows también podés usar `run.bat`.

## Modos de la aplicación

### 1. Descomposición

Carga CSV/Excel/EPW con timestamp + GHI (1/15/60 min; EPW horario), calcula DNI/DHI con tres modelos en paralelo y exporta CSV/Excel/JSON con quality score.

- DIRINT = Perez et al. (1992) vía `pvlib` (default)
- Opcional: humedad / punto de rocío en DIRINT (apagado por defecto)
- Si el archivo trae DNI/DHI: tabla de consistencia (no es exactitud salvo que sean mediciones)

### 2. Generación de EPW

1. Descargar la **plantilla** Excel (`plantilla_medidos_epw.xlsx`).
2. Completar medidas (puede ser un año parcial).
3. Subir plantilla + **EPW base**.
4. El programa:
   - completa DNI/DHI faltantes con el motor v1.1.0 (conserva los medidos);
   - sobrescribe en el EPW solo las horas con datos:
     - GHI, DNI, DHI
     - Dry Bulb, Atmospheric Pressure (kPa → Pa), Relative Humidity
   - el resto del EPW se conserva.
5. Descargar el EPW modificado y el reporte JSON.

## Plantilla EPW — columnas

| Columna | Etapa 1 (merge) | Notas |
|---------|-----------------|-------|
| `Date/Time` | Clave temporal | Inicio del intervalo `[t, t+1h]` |
| `Global Solar Wh/m2` | Sí | GHI; necesario para descomponer |
| `Normal Solar Wh/m2` | Sí | Vacío = calcular |
| `Diffuse Solar Wh/m2` | Sí | Vacío = calcular |
| `Dry Bulb Temperature C` | Sí | |
| `Atmospheric Pressure kPa` | Sí | En EPW se escribe en **Pa** (×1000) |
| `Relative Humidity %` | Sí | |
| `Dew Point Temperature C` | Reservado / opcional | Disponible para el pipeline científico |
| `Wind Speed m/s` | Reservado | Sin merge aún |
| `Wind Direction deg` | Reservado | Sin merge aún |

## Zona horaria (importante)

Para **descomponer** (geometría solar) usá la zona horaria **real de tus timestamps medidos**.

- Mendoza / Argentina hoy: **UTC−3**.
- Muchos EPW históricos argentinos dicen **−4** en `LOCATION`. Eso **no** significa que debas calcular con −4 si tus datos están en −3.

## Convención temporal plantilla ↔ EPW

- Plantilla: timestamp = **inicio** del intervalo horario.
- EPW EnergyPlus: `Hour` 1–24 = **hour ending**.
- Mapeo: `00:00` → Hour 1; `23:00` → Hour 24.

## Nota sobre lectores EPW

Hay dos usos distintos (no unificados a propósito):

- `io_handler.read_epw` / `load_file(.epw)` → entrada del **modo Descomposición**
- `epw_io.read_epw` → lectura/escritura del **modo Generación de EPW**

## Tests

```bash
python -m pytest tests/ -v
python test_pipeline.py
```

## Autores

Dr. Arq. Gustavo Barea Paci · Dra. Arq. Carolina Ganem — INAHE-CONICET

Mails (editables en `branding.py`):
- gbarea@mendoza-conicet.gob.ar
- cganem@mendoza-conicet.gob.ar

Logo: `assets/inahe_logo.jpg`
