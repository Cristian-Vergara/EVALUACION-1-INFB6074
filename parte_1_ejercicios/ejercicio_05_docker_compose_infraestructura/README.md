# Ejercicio 5 — Mini infraestructura con Docker Compose: Data Lake local con MinIO
**Herramientas:** Python · MinIO · DuckDB · Docker Compose

---

| Componente | Tipo | Puerto | Descripción |
|-----------|------|--------|-------------|
| `minio` | Servicio | 9000 (API) / 9001 (Web) | Data lake S3-compatible |
| `python_app` | Servicio | — | Sube y consulta datos |
| `red_infb6074` | Red interna | — | Comunicación entre servicios |
| `minio_data` | Volumen | — | Persistencia de datos |

---


## Cómo reproducir

### Requisitos
- Docker Desktop instalado y corriendo

### Pasos

```bash
# 1. Navegar a esta carpeta
cd parte_1_ejercicios/Parte_1/ejercicio_05_docker_compose_infraestructura

# 2. Levantar toda la infraestructura
docker compose up --build
```

Docker hace automáticamente:
1. Descarga la imagen `minio/minio` desde Docker Hub
2. Construye la imagen Python desde el `Dockerfile`
3. Crea la red interna `red_infb6074`
4. Crea el volumen persistente `minio_data`
5. Levanta MinIO → espera → levanta Python
6. Python sube los Parquet y ejecuta las consultas


### Ver resultados en la consola web

Mientras MinIO esté corriendo, entrá a:

```
http://localhost:9001
Usuario:    admin
Contraseña: secreto123
```

Verás el bucket `sensores-astronomicos` con los archivos Parquet subidos.

### Apagar

```bash
docker compose down
```

Los datos en MinIO persisten en el volumen — al volver a correr, el bucket ya existe.

### Apagar y borrar datos

```bash
docker compose down -v    # el -v elimina también el volumen
```

---

## Estructura del repositorio

```
ejercicio_05_docker_compose_infraestructura/
├── datos/
│   ├── lecturas_limpias.parquet     # Silver del Ej.4 — 9.048 lecturas
│   └── eventos_limpios.parquet      # Silver del Ej.4 — 903 eventos
├── scripts/
│   └── cargar_datos.py              # script principal Python
├── docker-compose.yml               # orquesta los dos servicios
├── Dockerfile                       # imagen del servicio Python
├── .dockerignore
├── requirements.txt
└── README.md
```

---


## Servicios y configuración

### MinIO

```yaml
image: minio/minio
ports:
  - "9000:9000"   # API S3 (Python se conecta acá)
  - "9001:9001"   # Consola web
environment:
  MINIO_ROOT_USER:     admin
  MINIO_ROOT_PASSWORD: secreto123
volumes:
  - minio_data:/data   # datos persisten al apagar
```

### Python

```yaml
build: .              # construido desde Dockerfile local
depends_on:
  - minio             # espera que MinIO esté corriendo
environment:
  MINIO_HOST:     minio    # hostname = nombre del servicio en la red
  MINIO_PORT:     "9000"
  MINIO_USER:     admin
  MINIO_PASSWORD: secreto123
```

**Por qué `MINIO_HOST: minio`:** dentro de la red interna de Docker Compose,
cada servicio es accesible por su nombre. Python se conecta a `minio:9000`
y Docker resuelve ese nombre a la IP del contenedor MinIO automáticamente.

---

## Flujo del script Python

```
1. Conectar    → Minio("minio:9000", access_key, secret_key)
2. Bucket      → crear "sensores-astronomicos" si no existe
3. Subir       → fput_object() × 2 archivos Parquet
4. Listar      → list_objects() → muestra nombres y tamaños
5. Consultar   → DuckDB + httpfs → 3 queries directo desde MinIO
```

---

## Consultas DuckDB directo desde MinIO (patrón lakehouse)

DuckDB puede consultar archivos Parquet almacenados en MinIO sin descargarlos,
usando la extensión `httpfs` configurada con las credenciales S3:

```python
conn.execute(f"""
    SET s3_endpoint        = 'minio:9000';
    SET s3_access_key_id   = 'admin';
    SET s3_secret_access_key = 'secreto123';
    SET s3_use_ssl         = false;
    SET s3_url_style       = 'path';
""")

df = conn.execute("""
    SELECT sensor_id, AVG(seeing_arcsec) AS seeing_promedio
    FROM read_parquet('s3://sensores-astronomicos/lecturas_limpias.parquet')
    GROUP BY sensor_id
    ORDER BY seeing_promedio ASC
""").df()
```

Este patrón se llama **lakehouse**: combina el almacenamiento económico de un
data lake (archivos en object storage) con la capacidad analítica SQL de un
data warehouse, sin mover los datos.

---

## Resultados de ejecución

| Métrica | Valor |
|---------|-------|
| Lecturas almacenadas en MinIO | 9.048 registros |
| Eventos almacenados en MinIO | 903 registros |
| Total en data lake | 9.951 registros |
| Mejor sensor (seeing) | SENS-004 Oeste — 0.635 arcsec |
| Instrumento más productivo | Espectrógrafo — 222 observaciones completadas |

---

## Script local vs mini infraestructura reproducible

| | Script local (`python script.py`) | Mini infraestructura (Docker Compose) |
|---|---|---|
| **Entorno** | Depende del Python instalado | Contenedor aislado, siempre igual |
| **Servicios** | Solo Python | Python + MinIO + red + volumen |
| **Reproducibilidad** | "Funciona en mi máquina" | Idéntico en cualquier máquina |
| **Persistencia** | Archivos en carpetas locales | Volumen gestionado por Docker |
| **Comunicación** | N/A | Red interna privada entre servicios |
| **Comando** | `python script.py` | `docker compose up` |
| **Escalabilidad** | No | Agregar servicios en docker-compose.yml |

La diferencia clave: Docker Compose define y levanta **toda la infraestructura**
con un solo comando, de forma reproducible e independiente del sistema operativo.

---

## Dependencias

| Librería | Versión | Uso |
|---------|---------|-----|
| `minio` | 7.2.15 | SDK para conectar a MinIO desde Python |
| `duckdb` | 1.5.2 | Consultas SQL sobre Parquet en MinIO |
| `pandas` | 3.0.3 | Visualización de resultados |

---

## Entorno

| Componente | Versión |
|-----------|---------|
| Python | 3.12-slim (imagen Docker) |
| MinIO | RELEASE.2025-09-07 |
| Docker Desktop | 4.x |
| macOS | M4 (arm64) |

---

## Declaración de herramientas de apoyo

Este ejercicio fue desarrollado con apoyo de IA (Claude, de Anthropic) como herramienta
de ayuda para desarrollar codigo, la IA no reemplazo el intelecto humano, toda desicion
fue tomada.