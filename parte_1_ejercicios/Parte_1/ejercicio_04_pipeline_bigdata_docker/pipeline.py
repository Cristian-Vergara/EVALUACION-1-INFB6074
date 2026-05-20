"""
pipeline.py
Orquestador principal del pipeline de datos astronómicos.
INFB6074 - Infraestructura para Ciencia de Datos - Ejercicio 4

Arquitectura medallón: Bronze → Silver → Gold
Dominio: Sensores ambientales del Observatorio Cerro Paranal (simulado).

Uso (local):
    python pipeline.py

Uso (Docker):
    docker build -t pipeline-infb6074 .
    docker run --rm -v $(pwd):/work pipeline-infb6074

Salidas:
    bronze/   → Parquet crudos (datos tal como llegaron)
    silver/   → Parquet limpios (después de validación)
    gold/     → Tablas analíticas (3 consultas DuckDB)
    metadata/ → catalogo.json + linaje.json
    metrics/  → reporte_calidad.json
"""

from datetime import datetime
from etapas import bronze, silver, gold, metadata
from pathlib import Path     


def main() -> None:
    inicio = datetime.now().isoformat(timespec="seconds")

    # Crear carpetas de salida si no existen (idempotente — si ya existen no hace nada)
    for carpeta in ["bronze", "silver", "gold", "metadata", "metrics"]:
        Path(carpeta).mkdir(exist_ok=True)

    print("=" * 60)
    print("=" * 60)
    print("PIPELINE ASTRONÓMICO — INFB6074")
    print(f"Inicio: {inicio}")
    print("=" * 60)

    # ── BRONZE: ingesta de datos crudos ───────────────────────────────────────
    print("\n[1/4] Zona Bronze — ingesta")
    df_lecturas_b, meta_b_l = bronze.ingestar_lecturas()
    df_eventos_b,  meta_b_e = bronze.ingestar_eventos()

    # ── SILVER: validación y limpieza ─────────────────────────────────────────
    print("\n[2/4] Zona Silver — validación y limpieza")
    df_lecturas_s, meta_s_l = silver.procesar_lecturas()
    df_eventos_s,  meta_s_e = silver.procesar_eventos()

    # ── GOLD: consultas analíticas con DuckDB ─────────────────────────────────
    print("\n[3/4] Zona Gold — agregaciones")
    _, meta_g_1 = gold.generar_condiciones_por_noche()
    _, meta_g_2 = gold.generar_resumen_sensores()
    _, meta_g_3 = gold.generar_observaciones_por_instrumento()

    # ── METADATA + MÉTRICAS: catálogo, linaje y reporte de calidad ────────────
    print("\n[4/4] Metadata y métricas")
    metadata.guardar_catalogo()
    metadata.guardar_linaje({
        "inicio":  inicio,
        "bronze":  [meta_b_l, meta_b_e],
        "silver":  [meta_s_l, meta_s_e],
        "gold":    [meta_g_1, meta_g_2, meta_g_3],
    })
    metadata.guardar_reporte_calidad([meta_s_l, meta_s_e])

    # ── RESUMEN FINAL ─────────────────────────────────────────────────────────
    fin = datetime.now()
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETADO")
    print(f"  Bronze:  {meta_b_l['filas']:,} lecturas + {meta_b_e['filas']:,} eventos ingestados")
    print(f"  Silver:  {meta_s_l['filas_validas']:,} lecturas + {meta_s_e['filas_validas']:,} eventos válidos")
    print(f"  Errores: {meta_s_l['filas_descartadas']:,} lecturas + {meta_s_e['filas_descartadas']:,} eventos descartados")
    print("  Gold:    3 tablas analíticas generadas")
    print(f"  Duración total: {(fin - datetime.fromisoformat(inicio)).seconds}s")
    print("=" * 60)


if __name__ == "__main__":
    main()