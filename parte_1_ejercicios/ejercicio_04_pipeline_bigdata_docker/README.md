# Ejercicio 4 — Pipeline Big Data Local con Python, Docker, Calidad y Parquet
---
## Descripción

Implementación de un pipeline reproducible de datos usando arquitectura medallón
(Bronze → Silver → Gold) con validación de calidad, catálogo, linaje y
almacenamiento columnar en formato Apache Parquet.

**Dominio:** sensores ambientales de un observatorio astronómico (simulado),
calibrados con datos reales del Observatorio Cerro Paranal, ESO Chile (2635 m s.n.m.).
Fuente de referencia: `archive.eso.org/wdb/wdb/asm/dimm_paranal/form`

---
## Cómo reproducir

### Opción A — Con Docker (recomendada)

```bash
# 1. Clonar el repositorio y navegar a esta carpeta
cd parte_1_ejercicios/Parte_1/ejercicio_04_pipeline_bigdata_docker

# 2.  Regenerar los datos sintéticos
python generar_datos.py

# 3. Construir la imagen Docker
docker build -t pipeline-infb6074 .

# 4. Ejecutar el pipeline
docker run --rm -v $(pwd):/work pipeline-infb6074
```

Los resultados se escriben directamente en las carpetas locales (`bronze/`, `silver/`, etc.)
gracias al montaje de volumen `-v $(pwd):/work`.

### Opción B — Sin Docker (entorno local)

```bash
# Con uv (recomendado)
uv sync
source .venv/bin/activate

# O con pip
pip install -r requirements.txt

# Ejecutar
python pipeline.py
```

---

## Fuentes de datos

### Fuente A — `datos/lecturas_sensores.csv`

Mediciones periódicas (cada 5 minutos) de 5 sensores ambientales durante 3 días.
Rangos calibrados con datos reales del ESO Paranal:

| Campo | Tipo | Rango válido | Descripción |
|-------|------|-------------|-------------|
| sensor_id | string | SENS-001 a SENS-005 | Identificador del sensor |
| timestamp | datetime | 2024-03-01 al 2024-03-07 | Fecha y hora UTC |
| ubicacion | string | Norte/Sur/Este/Oeste/Centro | Posición en el observatorio |
| temperatura_c | float64 | 14.0 – 20.0 °C | Temperatura nocturna del desierto |
| humedad_pct | float64 | 0.0 – 100.0 % | Humedad relativa (Atacama: 3-20%) |
| velocidad_viento_ms | float64 | ≥ 0 m/s | Velocidad del viento |
| presion_hpa | float64 | 700 – 900 hPa | Presión a 2635 m s.n.m. |
| seeing_arcsec | float64 | > 0 arcsec | Calidad óptica atmosférica (mediana ~0.64) |
| transparencia | float64 | 0.0 – 1.0 | Fracción de luz transmitida |

### Fuente B — `datos/eventos_observacion.jsonl`

Registro de 1.020 observaciones telescópicas (formato JSONL, un objeto JSON por línea):

| Campo | Tipo | Descripción |
|-------|------|-------------|
| obs_id | string | Identificador único (OBS-YYYY-XXXX) |
| sensor_id | string | Telescopio que realizó la observación |
| timestamp | datetime | Inicio de la observación |
| objeto_observado | string | Nombre del objeto celeste |
| magnitud | float64 | Magnitud aparente |
| ascension_recta | float64 | Coordenada AR en grados [0°, 360°] |
| declinacion | float64 | Coordenada Dec en grados [-90°, +90°] |
| duracion_min | int32 | Duración en minutos |
| instrumento | string | CCD / Espectrógrafo / Fotómetro |
| estado | string | completada / fallida / cancelada |

**Nota sobre los datos sintéticos:** los datos fueron generados con `generar_datos.py`
siguiendo los rangos reales del ESO Paranal. Se inyectó un 10% de errores controlados
para validar el funcionamiento de las reglas de calidad.

---

## Reglas de calidad (Silver)

### Lecturas (8 reglas)

| # | Regla | Descripción |
|---|-------|-------------|
| 1 | `error_temperatura_fuera_rango` | `temperatura_c == -999` (falla del sensor) |
| 2 | `error_humedad_fuera_rango` | `humedad_pct > 100` (físicamente imposible) |
| 3 | `error_sensor_id_nulo` | `sensor_id` es nulo (campo obligatorio) |
| 4 | `error_timestamp_futuro` | Timestamp en año 2027 (medición no ocurrida) |
| 5 | `error_seeing_negativo` | `seeing_arcsec < 0` (ángulo negativo) |
| 6 | `error_presion_nivel_mar` | `presion_hpa > 900` (sensor descalibrado) |
| 7 | `error_transparencia_invalida` | `transparencia > 1.0` (fracción > 1) |
| 8 | `error_lectura_duplicada` | Mismo `sensor_id` + `timestamp` duplicados |

### Eventos (5 reglas)

| # | Regla | Descripción |
|---|-------|-------------|
| 1 | `error_instrumento_invalido` | Instrumento fuera del catálogo (ej. RADAR) |
| 2 | `error_declinacion_invalida` | `declinacion < -90` o `> +90` grados |
| 3 | `error_timestamp_futuro` | Timestamp en año 2027 |
| 4 | `error_sensor_id_nulo` | `sensor_id` es nulo |
| 5 | `error_obs_id_duplicado` | `obs_id` repetido |

---

## Flujo del pipeline

```
datos/lecturas_sensores.csv  ──┐
                                ├── [Bronze] read_csv / read_ndjson
datos/eventos_observacion.jsonl ┘         ↓ Parquet crudos (sin modificar)
                                        bronze/
                                          ↓
                                [Silver] aplicar_reglas() + filter()
                                          ↓ Parquet limpios + tipados
                                        silver/
                                          ↓
                               [Gold] 3 consultas DuckDB
                                          ↓ Parquet analíticos
                                        gold/
                                          ↓
                             [Meta] catalogo.json + linaje.json
                                    metrics/reporte_calidad.json
```

---

## Consultas analíticas (Gold — DuckDB)

| Tabla | Pregunta que responde | Filas |
|-------|----------------------|-------|
| `condiciones_por_noche.parquet` | ¿Cuándo y dónde hubo mejor seeing? | 35 |
| `resumen_sensores.parquet` | ¿Qué sensor tiene mejor rendimiento? | 5 |
| `observaciones_por_instrumento.parquet` | ¿Qué instrumento completó más observaciones? | 9 |

---

## Por qué Docker aporta reproducibilidad

Sin Docker, el pipeline depende del Python instalado localmente, de las versiones
de las librerías del equipo y del sistema operativo. Con Docker:

- El `Dockerfile` fija `python:3.12-slim` como base.
- El `requirements.txt` fija las versiones exactas de cada librería.
- El comando `docker run --rm -v $(pwd):/work pipeline-infb6074` produce
  resultados idénticos en cualquier máquina (Mac M4, Windows, Linux, CI/CD).

---

## Entorno de desarrollo

| Componente | Versión |
|-----------|---------|
| Python | 3.12.13 |
| Docker Desktop | 4.73.0 |
| Docker Engine | 29.4.3 |
| polars | 1.40.1 |
| pandas | 3.0.3 |
| pyarrow | 24.0.0 |
| duckdb | 1.5.2 |
| macOS | M4 (arm64) |

---

## Declaración de herramientas de apoyo

Este ejercicio fue desarrollado con apoyo de IA (Claude, de Anthropic) como herramienta
de ayuda para desarrollar codigo, la IA no reemplazo el intelecto humano, toda desicion
fue tomada.