"""
etapas/metadata.py
Genera el catálogo de datos y el registro de linaje del pipeline.

Produce tres artefactos:
  - metadata/catalogo.json:       descripción de cada campo (tipo, regla, fuente)
  - metadata/linaje.json:         historial de transformaciones por etapa
  - metrics/reporte_calidad.json: resultados de las reglas de validación
"""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

RUTA_METADATA = Path("metadata")
RUTA_METRICS  = Path("metrics")


# ── Catálogo de datos ──────────────────────────────────────────────────────────
# Definición estática de cada campo en ambas fuentes de datos.
# Rangos calibrados con datos reales del ESO Paranal, Chile.

CATALOGO = {
    "version":      "1.0",
    "proyecto":     "Pipeline Astronómico - INFB6074",
    "observatorio": "Cerro Paranal (simulado), ESO Chile, 2635 m s.n.m.",
    "fuentes": {

        "lecturas_sensores": {
            "descripcion":     "Mediciones periódicas de condiciones ambientales (cada 5 min).",
            "archivo_origen":  "datos/lecturas_sensores.csv",
            "archivo_bronze":  "bronze/lecturas_raw.parquet",
            "archivo_silver":  "silver/lecturas_limpias.parquet",
            "campos": [
                {
                    "nombre":      "sensor_id",
                    "tipo":        "string",
                    "descripcion": "Identificador único del sensor.",
                    "fuente":      "lecturas_sensores.csv",
                    "obligatorio": True,
                    "regla":       "No nulo. Formato SENS-XXX.",
                },
                {
                    "nombre":      "timestamp",
                    "tipo":        "datetime",
                    "descripcion": "Fecha y hora de la medición (UTC).",
                    "fuente":      "lecturas_sensores.csv",
                    "obligatorio": True,
                    "regla":       "No nulo. No puede ser fecha futura.",
                },
                {
                    "nombre":      "ubicacion",
                    "tipo":        "string",
                    "descripcion": "Posición cardinal del sensor en el observatorio.",
                    "fuente":      "lecturas_sensores.csv",
                    "obligatorio": True,
                    "regla":       "Valores: Norte, Sur, Este, Oeste, Centro.",
                },
                {
                    "nombre":      "temperatura_c",
                    "tipo":        "float64",
                    "descripcion": "Temperatura ambiente en grados Celsius.",
                    "fuente":      "lecturas_sensores.csv",
                    "obligatorio": True,
                    "regla":       "Rango 14-20°C. Valor -999 indica falla del sensor.",
                },
                {
                    "nombre":      "humedad_pct",
                    "tipo":        "float64",
                    "descripcion": "Humedad relativa en porcentaje.",
                    "fuente":      "lecturas_sensores.csv",
                    "obligatorio": True,
                    "regla":       "Rango 0-100%. Atacama típico: 3-20%.",
                },
                {
                    "nombre":      "velocidad_viento_ms",
                    "tipo":        "float64",
                    "descripcion": "Velocidad del viento en metros por segundo.",
                    "fuente":      "lecturas_sensores.csv",
                    "obligatorio": False,
                    "regla":       "Valor >= 0.",
                },
                {
                    "nombre":      "presion_hpa",
                    "tipo":        "float64",
                    "descripcion": "Presión atmosférica. A 2635 m ~ 745 hPa.",
                    "fuente":      "lecturas_sensores.csv",
                    "obligatorio": False,
                    "regla":       "Rango 700-900 hPa. >900 indica sensor descalibrado.",
                },
                {
                    "nombre":      "seeing_arcsec",
                    "tipo":        "float64",
                    "descripcion": "Calidad óptica de la atmósfera (FWHM a 500 nm). Menor = mejor.",
                    "fuente":      "lecturas_sensores.csv",
                    "obligatorio": True,
                    "regla":       "Valor > 0. Mediana histórica Paranal: ~0.64 arcsec.",
                },
                {
                    "nombre":      "transparencia",
                    "tipo":        "float64",
                    "descripcion": "Fracción de luz transmitida por la atmósfera [0, 1].",
                    "fuente":      "lecturas_sensores.csv",
                    "obligatorio": False,
                    "regla":       "Rango 0.0-1.0. Valor >1 es físicamente imposible.",
                },
            ],
        },

        "eventos_observacion": {
            "descripcion":    "Registro de eventos de observación telescópica.",
            "archivo_origen": "datos/eventos_observacion.jsonl",
            "archivo_bronze": "bronze/eventos_raw.parquet",
            "archivo_silver": "silver/eventos_limpios.parquet",
            "campos": [
                {
                    "nombre":      "obs_id",
                    "tipo":        "string",
                    "descripcion": "Identificador único de la observación.",
                    "fuente":      "eventos_observacion.jsonl",
                    "obligatorio": True,
                    "regla":       "No nulo. Único. Formato OBS-YYYY-XXXX.",
                },
                {
                    "nombre":      "sensor_id",
                    "tipo":        "string",
                    "descripcion": "Telescopio que realizó la observación.",
                    "fuente":      "eventos_observacion.jsonl",
                    "obligatorio": True,
                    "regla":       "No nulo.",
                },
                {
                    "nombre":      "timestamp",
                    "tipo":        "datetime",
                    "descripcion": "Fecha y hora de inicio de la observación (UTC).",
                    "fuente":      "eventos_observacion.jsonl",
                    "obligatorio": True,
                    "regla":       "No nulo. No puede ser fecha futura.",
                },
                {
                    "nombre":      "objeto_observado",
                    "tipo":        "string",
                    "descripcion": "Nombre del objeto celeste observado.",
                    "fuente":      "eventos_observacion.jsonl",
                    "obligatorio": True,
                    "regla":       "No nulo.",
                },
                {
                    "nombre":      "magnitud",
                    "tipo":        "float64",
                    "descripcion": "Magnitud aparente del objeto observado.",
                    "fuente":      "eventos_observacion.jsonl",
                    "obligatorio": False,
                    "regla":       "Rango típico: -1.5 a 15.0.",
                },
                {
                    "nombre":      "ascension_recta",
                    "tipo":        "float64",
                    "descripcion": "Ascensión recta del objeto en grados.",
                    "fuente":      "eventos_observacion.jsonl",
                    "obligatorio": False,
                    "regla":       "Rango válido: 0.0 a 360.0°.",
                },
                {
                    "nombre":      "declinacion",
                    "tipo":        "float64",
                    "descripcion": "Declinación del objeto en grados.",
                    "fuente":      "eventos_observacion.jsonl",
                    "obligatorio": False,
                    "regla":       "Rango válido: -90.0 a +90.0°.",
                },
                {
                    "nombre":      "duracion_min",
                    "tipo":        "int32",
                    "descripcion": "Duración de la observación en minutos.",
                    "fuente":      "eventos_observacion.jsonl",
                    "obligatorio": True,
                    "regla":       "Valor > 0.",
                },
                {
                    "nombre":      "instrumento",
                    "tipo":        "string",
                    "descripcion": "Instrumento utilizado en la observación.",
                    "fuente":      "eventos_observacion.jsonl",
                    "obligatorio": True,
                    "regla":       "Valores: CCD, Espectrógrafo, Fotómetro.",
                },
                {
                    "nombre":      "estado",
                    "tipo":        "string",
                    "descripcion": "Resultado de la observación.",
                    "fuente":      "eventos_observacion.jsonl",
                    "obligatorio": True,
                    "regla":       "Valores: completada, fallida, cancelada.",
                },
            ],
        },
    },
}


# ── Funciones de escritura ─────────────────────────────────────────────────────

def guardar_catalogo() -> None:
    """Escribe metadata/catalogo.json con la descripción de todos los campos."""
    ruta = RUTA_METADATA / "catalogo.json"
    catalogo = {**CATALOGO, "generado": datetime.now().isoformat(timespec="seconds")}
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(catalogo, f, indent=2, ensure_ascii=False)
    print(f"  [Meta] Catálogo          → {ruta.name}")


def guardar_linaje(metas: dict) -> None:
    """
    Construye y escribe metadata/linaje.json.

    `metas` debe tener las claves 'inicio', 'bronze', 'silver', 'gold',
    cada una con la info devuelta por las funciones de cada etapa.
    """
    ruta = RUTA_METADATA / "linaje.json"
    linaje = {
        "pipeline":         "pipeline_astronomico_v1",
        "descripcion":      "Pipeline de sensores astronómicos - INFB6074",
        "script":           "pipeline.py",
        "ejecucion_inicio": metas.get("inicio", ""),
        "ejecucion_fin":    datetime.now().isoformat(timespec="seconds"),
        "etapas": {
            "bronze": metas.get("bronze", []),
            "silver": metas.get("silver", []),
            "gold":   metas.get("gold",   []),
        },
    }
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(linaje, f, indent=2, ensure_ascii=False)
    print(f"  [Meta] Linaje            → {ruta.name}")


def guardar_reporte_calidad(metas_silver: list[dict]) -> None:
    """
    Extrae los reportes de calidad de los metas de Silver
    y los escribe en metrics/reporte_calidad.json.
    """
    ruta = RUTA_METRICS / "reporte_calidad.json"
    reporte = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "fuentes":  {},
    }
    for meta in metas_silver:
        nombre = Path(meta.get("destino", "")).stem   # nombre sin extensión
        reporte["fuentes"][nombre] = {
            "filas_entrada":     meta.get("filas_entrada",     0),
            "filas_validas":     meta.get("filas_validas",     0),
            "filas_descartadas": meta.get("filas_descartadas", 0),
            "tasa_error_pct":    meta.get("tasa_error_pct",    0),
            "por_regla":         meta.get("reporte_calidad",   {}),
        }
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)
    print(f"  [Meta] Reporte calidad   → {ruta.name}")