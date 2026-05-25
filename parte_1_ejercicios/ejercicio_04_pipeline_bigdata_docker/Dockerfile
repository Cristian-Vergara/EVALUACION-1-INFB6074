FROM python:3.12-slim
WORKDIR /work

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el pipeline y todos sus módulos
COPY pipeline.py .
COPY etapas/ etapas/

CMD ["python", "pipeline.py"]