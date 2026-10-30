FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt requirements-mlops.txt ./
RUN python -m pip install -r requirements.txt -r requirements-mlops.txt

# Copias explícitas: ni las fuentes institucionales ni .git entran en la imagen.
COPY app.py ./
COPY src/ ./src/
COPY assets/ ./assets/
COPY mlops/ ./mlops/
# El tablero original necesita estos CSV; no montar outputs/ vacío encima.
COPY outputs/*.csv ./outputs/

EXPOSE 8050 5000

CMD ["python", "-c", "from app import app; app.run(host='0.0.0.0', port=8050, debug=False)"]
