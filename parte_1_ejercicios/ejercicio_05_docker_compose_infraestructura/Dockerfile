# Imagen base — misma que el Ej. 4 para consistencia
FROM python:3.12-slim

WORKDIR /work

# Dependencias primero (aprovecha caché de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Solo el script — los datos se montan en runtime
COPY scripts/ scripts/

CMD ["python", "scripts/cargar_datos.py"]