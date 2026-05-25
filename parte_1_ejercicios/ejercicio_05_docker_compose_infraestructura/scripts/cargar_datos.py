"""
Flujo:
  1. Conectar a MinIO (data lake local)
  2. Crear bucket "sensores-astronomicos"
  3. Subir los Parquet de Silver (Ej.4)
  4. Listar archivos en el bucket
  5. Consultar los Parquet directo desde MinIO con DuckDB (patrón lakehouse)
"""

import os
from pathlib import Path
import time
import duckdb
from minio import Minio

# ── Configuración desde variables de entorno ──────────────────────────────────
MINIO_HOST     = os.environ.get("MINIO_HOST",     "localhost")
MINIO_PORT     = os.environ.get("MINIO_PORT",     "9000")
MINIO_USER     = os.environ.get("MINIO_USER",     "admin")
MINIO_PASSWORD = os.environ.get("MINIO_PASSWORD", "secreto123")
BUCKET         = "sensores-astronomicos"
RUTA_DATOS     = Path("datos")


# ── 1. Conexión ───────────────────────────────────────────────────────────────

def conectar_minio() -> Minio:
    """Conecta al servidor MinIO y retorna el cliente."""
    client = Minio(
        f"{MINIO_HOST}:{MINIO_PORT}",
        access_key=MINIO_USER,
        secret_key=MINIO_PASSWORD,
        secure=False,
    )
    print(f"  Conectado a MinIO en {MINIO_HOST}:{MINIO_PORT}")
    return client


# ── 2. Bucket ─────────────────────────────────────────────────────────────────

def crear_bucket(client: Minio) -> None:
    """Crea el bucket si no existe."""
    if not client.bucket_exists(BUCKET):
        client.make_bucket(BUCKET)
        print(f"  Bucket '{BUCKET}' creado")
    else:
        print(f"  Bucket '{BUCKET}' ya existía")


# ── 3. Subir archivos ─────────────────────────────────────────────────────────

def subir_parquet(client: Minio) -> None:
    """Sube todos los Parquet de datos/ al bucket."""
    archivos = sorted(RUTA_DATOS.glob("*.parquet"))
    if not archivos:
        print("  No se encontraron archivos Parquet en datos/")
        return
    for archivo in archivos:
        client.fput_object(
            BUCKET,
            archivo.name,
            str(archivo),
            content_type="application/octet-stream",
        )
        kb = archivo.stat().st_size / 1024
        print(f"  Subido: {archivo.name}  ({kb:.1f} KB)")


# ── 4. Listar archivos ────────────────────────────────────────────────────────

def listar_bucket(client: Minio) -> None:
    """Lista los objetos guardados en el bucket."""
    objetos = list(client.list_objects(BUCKET))
    print(f"\n  Archivos en '{BUCKET}':")
    for obj in objetos:
        print(f"    {obj.object_name:<40s}  {obj.size/1024:7.1f} KB")


# ── 5. Consultas DuckDB directo desde MinIO ───────────────────────────────────

def consultar_desde_minio() -> None:
    """
    Consulta los Parquet directo desde MinIO sin descargarlos.
    Patrón lakehouse: DuckDB + httpfs + S3-compatible storage.
    """
    conn = duckdb.connect()

    # Configurar DuckDB para leer desde MinIO (S3-compatible, path-style)
    conn.execute(f"""
        INSTALL httpfs;
        LOAD httpfs;
        SET s3_endpoint        = '{MINIO_HOST}:{MINIO_PORT}';
        SET s3_access_key_id   = '{MINIO_USER}';
        SET s3_secret_access_key = '{MINIO_PASSWORD}';
        SET s3_use_ssl         = false;
        SET s3_url_style       = 'path';
    """)

    # ── Consulta 1: seeing promedio por sensor ────────────────────────────────
    print("\n  Consulta 1 — Seeing promedio por sensor (menor = mejor):")
    df1 = conn.execute(f"""
        SELECT
            sensor_id,
            ubicacion,
            ROUND(AVG(seeing_arcsec), 3)  AS seeing_promedio,
            ROUND(MIN(seeing_arcsec), 3)  AS seeing_minimo,
            COUNT(*)                       AS n_lecturas
        FROM read_parquet('s3://{BUCKET}/lecturas_limpias.parquet')
        GROUP BY sensor_id, ubicacion
        ORDER BY seeing_promedio ASC
    """).df()
    print(df1.to_string(index=False))

    # ── Consulta 2: observaciones por instrumento y estado ────────────────────
    print("\n  Consulta 2 — Observaciones por instrumento:")
    df2 = conn.execute(f"""
        SELECT
            instrumento,
            estado,
            COUNT(*)                       AS total,
            ROUND(AVG(duracion_min), 1)    AS duracion_promedio_min
        FROM read_parquet('s3://{BUCKET}/eventos_limpios.parquet')
        GROUP BY instrumento, estado
        ORDER BY instrumento, total DESC
    """).df()
    print(df2.to_string(index=False))

    # ── Consulta 3: resumen del data lake ─────────────────────────────────────
    print("\n  Consulta 3 — Resumen del data lake MinIO:")
    n_l = conn.execute(f"""
        SELECT COUNT(*) FROM read_parquet('s3://{BUCKET}/lecturas_limpias.parquet')
    """).fetchone()[0]
    n_e = conn.execute(f"""
        SELECT COUNT(*) FROM read_parquet('s3://{BUCKET}/eventos_limpios.parquet')
    """).fetchone()[0]
    print(f"    Lecturas almacenadas:  {n_l:,} registros")
    print(f"    Eventos almacenados:   {n_e:,} registros")
    print(f"    Total en data lake:    {n_l + n_e:,} registros")

    conn.close()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 55)
    print("DATA LAKE LOCAL CON MINIO — INFB6074")
    print("Docker Compose: MinIO + Python + DuckDB")
    print("=" * 55)
    print("\n  Esperando que MinIO inicie...")
    time.sleep(6)

    print("\n[1/4] Conectando a MinIO...")
    print("\n[1/4] Conectando a MinIO...")
    client = conectar_minio()

    print("\n[2/4] Preparando bucket...")
    crear_bucket(client)

    print("\n[3/4] Subiendo archivos Parquet (Silver del Ej.4)...")
    subir_parquet(client)

    print("\n[4/4] Consultando data lake con DuckDB...")
    listar_bucket(client)
    consultar_desde_minio()

    print("\n" + "=" * 55)
    print("COMPLETADO")
    print("  Consola web MinIO: http://localhost:9001")
    print(f"  Usuario:           {MINIO_USER}")
    print(f"  Contraseña:        {MINIO_PASSWORD}")
    print(f"  Bucket:            {BUCKET}")
    print("=" * 55)


if __name__ == "__main__":
    main()