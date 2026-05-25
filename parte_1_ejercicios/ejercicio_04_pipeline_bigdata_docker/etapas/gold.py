"""
etapas/gold.py
Zona Gold: tablas analíticas listas para consumo.

Lee los Parquet limpios de Silver y genera 3 tablas de agregación
usando DuckDB como motor de consultas SQL sobre Parquet.
Las 3 tablas responden preguntas concretas del observatorio:
  1. ¿Cuándo y dónde hubo mejores condiciones de observación?
  2. ¿Qué sensor tiene mejor rendimiento promedio?
  3. ¿Qué instrumento completó más observaciones exitosas?
"""

from __future__ import annotations
from datetime import datetime
from pathlib import Path

import duckdb
import polars as pl

RUTA_SILVER = Path("silver")
RUTA_GOLD   = Path("gold")


def generar_condiciones_por_noche() -> tuple[pl.DataFrame, dict]:
    """
    Tabla 1: condiciones_por_noche.parquet
    Promedia seeing, temperatura, humedad y viento por sensor y fecha.
    Ordenada por seeing_promedio ASC → las mejores noches primero.
    """
    ruta_origen  = RUTA_SILVER / "lecturas_limpias.parquet"
    ruta_destino = RUTA_GOLD   / "condiciones_por_noche.parquet"

    conn = duckdb.connect()

    # DuckDB puede leer Parquet directamente con read_parquet()
    # sin necesidad de cargar todo en memoria primero
    df = conn.execute(f"""
        SELECT
            sensor_id,
            ubicacion,
            CAST(timestamp AS DATE)              AS fecha,
            ROUND(AVG(seeing_arcsec),  3)        AS seeing_promedio,
            ROUND(MIN(seeing_arcsec),  3)        AS seeing_minimo,
            ROUND(AVG(temperatura_c),  2)        AS temperatura_promedio,
            ROUND(AVG(humedad_pct),    2)        AS humedad_promedio,
            ROUND(AVG(velocidad_viento_ms), 2)   AS viento_promedio,
            ROUND(AVG(transparencia),  3)        AS transparencia_promedio,
            COUNT(*)                             AS n_lecturas
        FROM read_parquet('{ruta_origen.as_posix()}')
        GROUP BY sensor_id, ubicacion, CAST(timestamp AS DATE)
        ORDER BY seeing_promedio ASC
    """).pl()   # .pl() devuelve un DataFrame de Polars directamente

    df.to_pandas().to_parquet(str(ruta_destino), engine="pyarrow", index=False)

    print(f"  [Gold] Condiciones por noche:        {df.height:,} filas → {ruta_destino.name}")

    meta = {
        "tabla":             "condiciones_por_noche",
        "destino":           str(ruta_destino),
        "filas":             df.height,
        "pregunta":          "¿Cuándo y dónde hubo mejores condiciones de observación?",
        "timestamp_proceso": datetime.now().isoformat(timespec="seconds"),
    }
    return df, meta


def generar_resumen_sensores() -> tuple[pl.DataFrame, dict]:
    """
    Tabla 2: resumen_sensores.parquet
    Estadísticas de desempeño por sensor: seeing, temperatura, transparencia.
    """
    ruta_origen  = RUTA_SILVER / "lecturas_limpias.parquet"
    ruta_destino = RUTA_GOLD   / "resumen_sensores.parquet"

    conn = duckdb.connect()

    df = conn.execute(f"""
        SELECT
            sensor_id,
            ubicacion,
            COUNT(*)                            AS total_lecturas,
            ROUND(AVG(seeing_arcsec),   3)      AS seeing_promedio,
            ROUND(STDDEV(seeing_arcsec),3)      AS seeing_desv_std,
            ROUND(MIN(seeing_arcsec),   3)      AS seeing_minimo,
            ROUND(AVG(transparencia),   3)      AS transparencia_promedio,
            ROUND(MIN(temperatura_c),   2)      AS temp_minima,
            ROUND(MAX(temperatura_c),   2)      AS temp_maxima,
            ROUND(AVG(humedad_pct),     2)      AS humedad_promedio
        FROM read_parquet('{ruta_origen.as_posix()}')
        GROUP BY sensor_id, ubicacion
        ORDER BY seeing_promedio ASC
    """).pl()

    df.to_pandas().to_parquet(str(ruta_destino), engine="pyarrow", index=False)

    print(f"  [Gold] Resumen sensores:             {df.height:,} filas → {ruta_destino.name}")

    meta = {
        "tabla":             "resumen_sensores",
        "destino":           str(ruta_destino),
        "filas":             df.height,
        "pregunta":          "¿Qué sensor tiene mejor rendimiento de seeing?",
        "timestamp_proceso": datetime.now().isoformat(timespec="seconds"),
    }
    return df, meta


def generar_observaciones_por_instrumento() -> tuple[pl.DataFrame, dict]:
    """
    Tabla 3: observaciones_por_instrumento.parquet
    Conteo y estadísticas de observaciones por instrumento y estado.
    """
    ruta_origen  = RUTA_SILVER / "eventos_limpios.parquet"
    ruta_destino = RUTA_GOLD   / "observaciones_por_instrumento.parquet"

    conn = duckdb.connect()

    df = conn.execute(f"""
        SELECT
            instrumento,
            estado,
            COUNT(*)                            AS total_observaciones,
            ROUND(AVG(duracion_min), 1)         AS duracion_promedio_min,
            ROUND(MIN(duracion_min), 1)         AS duracion_minima_min,
            ROUND(MAX(duracion_min), 1)         AS duracion_maxima_min,
            ROUND(AVG(magnitud),     2)         AS magnitud_promedio,
            COUNT(DISTINCT objeto_observado)    AS objetos_unicos,
            COUNT(DISTINCT sensor_id)           AS telescopios_activos
        FROM read_parquet('{ruta_origen.as_posix()}')
        GROUP BY instrumento, estado
        ORDER BY instrumento, total_observaciones DESC
    """).pl()

    df.to_pandas().to_parquet(str(ruta_destino), engine="pyarrow", index=False)

    print(f"  [Gold] Por instrumento:              {df.height:,} filas → {ruta_destino.name}")

    meta = {
        "tabla":             "observaciones_por_instrumento",
        "destino":           str(ruta_destino),
        "filas":             df.height,
        "pregunta":          "¿Qué instrumento completó más observaciones exitosas?",
        "timestamp_proceso": datetime.now().isoformat(timespec="seconds"),
    }
    return df, meta