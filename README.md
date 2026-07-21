# Generación de EPW

Herramienta **INAHE-CONICET** para:

1. Descomponer **GHI → DNI + DHI** (modelos DIRINT / Erbs)
2. Generar un **EPW modificado** a partir de datos medidos + EPW base

**Autores:** Dr. Arq. Gustavo Barea Paci · Dra. Arq. Carolina Ganem

## Ejecutar en tu PC

```bash
pip install -r requirements.txt
streamlit run app_solar.py
```

En Windows también podés usar `run.bat`.

## Modos de la aplicación

### 1. Descomposición

Carga CSV/Excel con timestamp + GHI (1/15/60 min), calcula DNI/DHI y exporta CSV/Excel/JSON con quality score.

### 2. Generación de EPW

1. Descargar la **plantilla** Excel (`plantilla_medidos_epw.xlsx`).
2. Completar medidas (puede ser un año parcial).
3. Subir plantilla + **EPW base**.
4. El programa:
   - completa DNI/DHI faltantes (conserva los medidos);
   - sobrescribe en el EPW solo las horas con datos:
     - GHI, DNI, DHI
     - Dry Bulb, Atmospheric Pressure (kPa → Pa), Relative Humidity
   - el resto del EPW se conserva.
5. Descargar el EPW modificado y el reporte JSON.

## Plantilla — columnas

| Columna | Etapa 1 (merge) | Notas |
|---------|-----------------|-------|
| `Date/Time` | Clave temporal | Inicio del intervalo `[t, t+1h]` |
| `Global Solar Wh/m2` | Sí | GHI; necesario para descomponer |
| `Normal Solar Wh/m2` | Sí | Vacío = calcular |
| `Diffuse Solar Wh/m2` | Sí | Vacío = calcular |
| `Dry Bulb Temperature C` | Sí | |
| `Atmospheric Pressure kPa` | Sí | En EPW se escribe en **Pa** (×1000) |
| `Relative Humidity %` | Sí | |
| `Dew Point Temperature C` | Reservado | Sin merge aún |
| `Wind Speed m/s` | Reservado | Sin merge aún |
| `Wind Direction deg` | Reservado | Sin merge aún |

## Zona horaria (importante)

Para **descomponer** (geometría solar) usá la zona horaria **real de tus timestamps medidos**.

- Mendoza / Argentina hoy: **UTC−3**.
- Muchos EPW históricos argentinos dicen **−4** en `LOCATION` (convención vieja / DST). Eso **no** significa que debas calcular con −4 si tus datos están en −3.

Recomendación práctica:
1. Sitio: lat/lon del EPW (se autocompletan al subir el archivo).
2. Tz: el de tus mediciones (p. ej. −3).
3. Activar **“Actualizar tz en cabecera LOCATION”** para que EnergyPlus use el mismo tz que tus datos.

## Convención temporal plantilla ↔ EPW

- Plantilla: timestamp = **inicio** del intervalo horario.
- EPW EnergyPlus: `Hour` 1–24 = **hour ending**.
- Mapeo: `00:00` → Hour 1; `23:00` → Hour 24.
- Join por `(month, day, hour)`; el año del EPW se conserva (útil para TMY).

## Tests

```bash
python -m pytest tests/ -v
```

## Autores

Dr. Arq. Gustavo Barea Paci · Dra. Arq. Carolina Ganem — INAHE-CONICET

Mails (editables en `branding.py`):
- gbarea@mendoza-conicet.gob.ar
- cganem@mendoza-conicet.gob.ar

Logo: `assets/inahe_logo.jpg`
