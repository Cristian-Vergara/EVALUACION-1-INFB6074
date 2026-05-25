"""
etapas/bronze.py
Zona Bronze: ingesta de datos crudos.

Lee las dos fuentes originales (CSV y JSONL) sin ninguna modificación
y las persiste en formato Parquet en bronze/.

Principio de la zona Bronze: los datos se guardan TAL COMO LLEGARON.
"""

from __future__ import annotations
from datetime import datetime
from pathlib import Path

import polars as pl


RUTA_DATOS  = Path("datos")
RUTA_BRONZE = Path("bronze")


def ingestar_lecturas() -> tuple[pl.DataFrame, dict]:
    """
    Lee datos/lecturas_sensores.csv y guarda bronze/lecturas_raw.parquet.

    Retorna:
      - df:   DataFrame crudo tal como llegó del CSV
      - meta: info de la ingesta (filas, columnas, timestamp) para el linaje
    """
    ruta_origen  = RUTA_DATOS  / "lecturas_sensores.csv"
    ruta_destino = RUTA_BRONZE / "lecturas_raw.parquet"

    # Polars lee el CSV inferiendo tipos automáticamente.
    # null_values cubre las representaciones comunes de "sin dato".
    # No aplicamos ninguna transformación — Bronze es fiel al origen.
    df = pl.read_csv(
        ruta_origen,
        null_values=["", "NULL", "null", "NA"],
    )

    # Escritura Parquet vía pandas + pyarrow.
    # La conversión Polars → Pandas es eficiente porque ambas librerías
    # usan Apache Arrow como formato interno de memoria.
    df.to_pandas().to_parquet(
        str(ruta_destino),
        engine="pyarrow",
        index=False,
    )

    meta = {
        "fuente":            "lecturas_sensores.csv",
        "origen":            str(ruta_origen),
        "destino":           str(ruta_destino),
        "filas":             df.height,
        "columnas":          df.width,
        "nombres_columnas":  df.columns,
        "timestamp_ingesta": datetime.now().isoformat(timespec="seconds"),
    }

    print(f"  [Bronze] Lecturas: {df.height:,} filas, {df.width} cols → {ruta_destino.name}")
    return df, meta


def ingestar_eventos() -> tuple[pl.DataFrame, dict]:
    """
    Lee datos/eventos_observacion.jsonl y guarda bronze/eventos_raw.parquet.

    Polars lee NDJSON (Newline-Delimited JSON) nativamente:
    cada línea del .jsonl es un objeto JSON independiente.
    """
    ruta_origen  = RUTA_DATOS  / "eventos_observacion.jsonl"
    ruta_destino = RUTA_BRONZE / "eventos_raw.parquet"

    # read_ndjson = leer JSON con un objeto por línea (formato .jsonl)
    df = pl.read_ndjson(ruta_origen)

    df.to_pandas().to_parquet(
        str(ruta_destino),
        engine="pyarrow",
        index=False,
    )

    meta = {
        "fuente":            "eventos_observacion.jsonl",
        "origen":            str(ruta_origen),
        "destino":           str(ruta_destino),
        "filas":             df.height,
        "columnas":          df.width,
        "nombres_columnas":  df.columns,
        "timestamp_ingesta": datetime.now().isoformat(timespec="seconds"),
    }

    print(f"  [Bronze] Eventos:  {df.height:,} filas, {df.width} cols → {ruta_destino.name}")
    return df, meta