"""
etapas/silver.py
Zona Silver: validación, limpieza y tipado de datos.

Lee los Parquet crudos de Bronze, aplica las reglas de calidad de calidad.py,
retiene solo las filas válidas, corrige los tipos de datos y guarda en silver/.

Silver es la "única fuente de verdad" del pipeline:
datos limpios, tipados y listos para análisis.
"""

from __future__ import annotations
from datetime import datetime
from pathlib import Path

import polars as pl

from etapas.calidad import (
    REGLAS_LECTURAS,
    REGLAS_EVENTOS,
    aplicar_reglas,
    generar_reporte,
)

RUTA_BRONZE = Path("bronze")
RUTA_SILVER = Path("silver")


def procesar_lecturas() -> tuple[pl.DataFrame, dict]:
    """
    Lee bronze/lecturas_raw.parquet, aplica reglas de calidad,
    limpia tipos y guarda silver/lecturas_limpias.parquet.

    Retorna:
      - df_silver: DataFrame limpio y tipado
      - meta:      estadísticas del proceso (para linaje y métricas)
    """
    ruta_origen  = RUTA_BRONZE / "lecturas_raw.parquet"
    ruta_destino = RUTA_SILVER / "lecturas_limpias.parquet"

    # ── Leer desde Bronze ─────────────────────────────────────────────────────
    df_bronze = pl.read_parquet(ruta_origen)

    # ── Aplicar reglas → agrega una columna booleana por cada regla ───────────
    df_flagged = aplicar_reglas(df_bronze, REGLAS_LECTURAS)

    # ── Generar reporte ANTES de filtrar (para documentar cuántos errores hubo)
    reporte = generar_reporte(df_flagged, REGLAS_LECTURAS)

    # ── Filtrar: solo filas que no tienen NINGÚN error ─────────────────────────
    df_valido = df_flagged.filter(~pl.col("tiene_error"))

    # ── Eliminar columnas de flags (ya cumplieron su función) ─────────────────
    columnas_flags = list(REGLAS_LECTURAS.keys()) + ["tiene_error"]
    df_sin_flags = df_valido.drop(columnas_flags)

    # ── Corregir tipos de datos ───────────────────────────────────────────────
    # Bronze los trajo como los infirió Polars desde el CSV.
    # Silver garantiza los tipos definitivos que usará Gold.
    df_silver = df_sin_flags.with_columns([
        # Timestamp: string ISO → datetime nativo de Polars
        pl.col("timestamp").str.to_datetime("%Y-%m-%dT%H:%M:%S"),
        # Numéricos: asegurar precisión float
        pl.col("temperatura_c").cast(pl.Float64),
        pl.col("humedad_pct").cast(pl.Float64),
        pl.col("velocidad_viento_ms").cast(pl.Float64),
        pl.col("presion_hpa").cast(pl.Float64),
        pl.col("seeing_arcsec").cast(pl.Float64),
        pl.col("transparencia").cast(pl.Float64),
    ])

    # ── Guardar en Silver ─────────────────────────────────────────────────────
    df_silver.to_pandas().to_parquet(
        str(ruta_destino),
        engine="pyarrow",
        index=False,
    )

    n_entrada   = df_bronze.height
    n_validas   = df_silver.height
    n_descartadas = n_entrada - n_validas

    print(f"  [Silver] Lecturas: {n_entrada:,} entrada → "
          f"{n_validas:,} válidas, {n_descartadas:,} descartadas "
          f"({n_descartadas / n_entrada * 100:.1f}%)")

    meta = {
        "origen":            str(ruta_origen),
        "destino":           str(ruta_destino),
        "filas_entrada":     n_entrada,
        "filas_validas":     n_validas,
        "filas_descartadas": n_descartadas,
        "tasa_error_pct":    round(n_descartadas / n_entrada * 100, 2),
        "timestamp_proceso": datetime.now().isoformat(timespec="seconds"),
        "reporte_calidad":   reporte,
    }

    return df_silver, meta


def procesar_eventos() -> tuple[pl.DataFrame, dict]:
    """
    Lee bronze/eventos_raw.parquet, valida, limpia tipos
    y guarda silver/eventos_limpios.parquet.
    """
    ruta_origen  = RUTA_BRONZE / "eventos_raw.parquet"
    ruta_destino = RUTA_SILVER / "eventos_limpios.parquet"

    df_bronze  = pl.read_parquet(ruta_origen)
    df_flagged = aplicar_reglas(df_bronze, REGLAS_EVENTOS)
    reporte    = generar_reporte(df_flagged, REGLAS_EVENTOS)

    df_valido = df_flagged.filter(~pl.col("tiene_error"))

    columnas_flags = list(REGLAS_EVENTOS.keys()) + ["tiene_error"]

    df_silver = (
        df_valido
        .drop(columnas_flags)
        .with_columns([
            pl.col("timestamp").str.to_datetime("%Y-%m-%dT%H:%M:%S"),
            pl.col("magnitud").cast(pl.Float64),
            pl.col("ascension_recta").cast(pl.Float64),
            pl.col("declinacion").cast(pl.Float64),
            pl.col("duracion_min").cast(pl.Int32),
        ])
    )

    df_silver.to_pandas().to_parquet(
        str(ruta_destino),
        engine="pyarrow",
        index=False,
    )

    n_entrada     = df_bronze.height
    n_validos     = df_silver.height
    n_descartados = n_entrada - n_validos

    print(f"  [Silver] Eventos:  {n_entrada:,} entrada → "
          f"{n_validos:,} válidos, {n_descartados:,} descartados "
          f"({n_descartados / n_entrada * 100:.1f}%)")

    meta = {
        "origen":            str(ruta_origen),
        "destino":           str(ruta_destino),
        "filas_entrada":     n_entrada,
        "filas_validas":     n_validos,
        "filas_descartadas": n_descartados,
        "tasa_error_pct":    round(n_descartados / n_entrada * 100, 2),
        "timestamp_proceso": datetime.now().isoformat(timespec="seconds"),
        "reporte_calidad":   reporte,
    }

    return df_silver, meta