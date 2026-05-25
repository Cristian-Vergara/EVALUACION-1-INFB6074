"""
etapas/calidad.py
Reglas de validación de calidad para el pipeline astronómico.
Rangos calibrados con datos reales del Observatorio Cerro Paranal,
ESO Chile (2635m de altitud), descargados de:
  archive.eso.org/wdb/wdb/asm/dimm_paranal/form
  archive.eso.org/wdb/wdb/asm/meteo_paranal/form
"""

from __future__ import annotations
import polars as pl


# Instrumentos válidos del observatorio 
INSTRUMENTOS_VALIDOS = ["CCD", "Espectrógrafo", "Fotómetro"]


# Reglas para lecturas_sensores.csv 
# Cada entrada es: nombre_de_la_regla → expresión Polars que devuelve True
# cuando una fila tiene ERROR (True = problema, False = ok).

REGLAS_LECTURAS: dict[str, pl.Expr] = {

    # 1. Temperatura de sensor roto (-999 es el valor sentinel del hardware)
    "error_temperatura_fuera_rango":
        pl.col("temperatura_c") == -999.0,

    # 2. Humedad imposible (> 100% no existe físicamente)
    "error_humedad_fuera_rango":
        pl.col("humedad_pct") > 100.0,

    # 3. Campo obligatorio nulo (sensor_id identifica al dispositivo)
    "error_sensor_id_nulo":
        pl.col("sensor_id").is_null(),

    # 4. Timestamp en el futuro (medición aún no puede haber ocurrido)
    "error_timestamp_futuro":
        pl.col("timestamp").str.starts_with("2027"),

    # 5. Seeing negativo (ángulo de abertura no puede ser negativo)
    "error_seeing_negativo":
        pl.col("seeing_arcsec") < 0.0,

    # 6. Presión de nivel del mar (sensor descalibrado, Paranal está a 2635m)
    "error_presion_nivel_mar":
        pl.col("presion_hpa") > 900.0,

    # 7. Transparencia fuera de rango [0, 1] (es una fracción, no puede > 1)
    "error_transparencia_invalida":
        pl.col("transparencia") > 1.0,

    # 8. Lectura duplicada: mismo sensor en el mismo timestamp
    "error_lectura_duplicada":
        pl.struct(["sensor_id", "timestamp"]).is_duplicated(),
}


#  Reglas para eventos_observacion.jsonl
REGLAS_EVENTOS: dict[str, pl.Expr] = {

    # 1. Instrumento no reconocido en el catálogo del observatorio
    "error_instrumento_invalido":
        ~pl.col("instrumento").is_in(INSTRUMENTOS_VALIDOS),

    # 2. Declinación fuera del rango astronómico válido [-90°, +90°]
    "error_declinacion_invalida":
        (pl.col("declinacion") < -90.0) | (pl.col("declinacion") > 90.0),

    # 3. Timestamp en el futuro
    "error_timestamp_futuro":
        pl.col("timestamp").str.starts_with("2027"),

    # 4. sensor_id nulo (no sabemos qué telescopio realizó la observación)
    "error_sensor_id_nulo":
        pl.col("sensor_id").is_null(),

    # 5. obs_id duplicado (dos eventos no pueden tener el mismo identificador)
    "error_obs_id_duplicado":
        pl.col("obs_id").is_duplicated(),
}

#  Funciones de validación 

def aplicar_reglas(
    df: pl.DataFrame,
    reglas: dict[str, pl.Expr],
) -> pl.DataFrame:
    """
    Agrega una columna booleana por cada regla al DataFrame.
    True  → la fila VIOLA esa regla (tiene error).
    False → la fila PASA esa regla (ok).
    Agrega también la columna 'tiene_error': True si viola al menos una regla.
    """
    # Una columna por regla
    df = df.with_columns([
        expr.alias(nombre)
        for nombre, expr in reglas.items()
    ])

    # Columna resumen: True si CUALQUIER regla se viola
    nombres_error = list(reglas.keys())
    df = df.with_columns(
        pl.any_horizontal(nombres_error).alias("tiene_error")
    )

    return df


def generar_reporte(
    df_con_flags: pl.DataFrame,
    reglas: dict[str, pl.Expr],
) -> dict:
    """
    Retorna un diccionario con estadísticas por regla y un resumen global.
    Sirve como input para metrics/reporte_calidad.json.
    """
    total = len(df_con_flags)
    reporte: dict = {}

    for nombre in reglas.keys():
        n = df_con_flags.filter(pl.col(nombre)).height
        reporte[nombre] = {
            "total_invalidos": n,
            "porcentaje":      round(n / total * 100, 2) if total > 0 else 0.0,
        }

    # Resumen global
    n_invalidos = df_con_flags.filter(pl.col("tiene_error")).height
    reporte["__resumen__"] = {
        "total_filas":     total,
        "filas_validas":   total - n_invalidos,
        "filas_invalidas": n_invalidos,
        "tasa_error_pct":  round(n_invalidos / total * 100, 2) if total > 0 else 0.0,
    }

    return reporte