# Localizador inteligente de objetos · Práctica 10
# Imagen de la app completa: API en FastAPI (main.py) + app web ya compilada.

# ---------- Etapa 1: compilar la app web ----------
# Imagen oficial de Node; solo se usa para compilar y no queda en la imagen final.
FROM node:22-slim AS web
# Carpeta de trabajo de esta etapa.
WORKDIR /web
# Primero solo los archivos de dependencias, para que esta capa se reutilice si no cambian.
COPY frontend/package.json frontend/package-lock.json ./
# Instala exactamente las versiones del package-lock.
RUN npm ci
# Después el código de la app web (cambia seguido, por eso va al final).
COPY frontend/ ./
# Compila la app web a archivos estáticos en /web/dist.
RUN npm run build

# ---------- Etapa 2: imagen final ----------
# Imagen oficial de Python, versión slim: la misma 3.12 de las Lambdas y sin herramientas que no se usan.
FROM python:3.12-slim
# No generar archivos .pyc, mostrar los logs al momento y no guardar la caché de pip.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
# Valores por defecto de la configuración; en cada ambiente se cambian con -e al ejecutar.
ENV PORT=8000 \
    LOCALIZADOR_BD=/datos/localizador.db \
    CORS_ALLOW_ORIGIN=http://localhost:8000 \
    LOG_LEVEL=INFO
# Carpeta de la aplicación dentro del contenedor.
WORKDIR /app
# Primero la lista de dependencias...
COPY requirements-local.txt .
# ...y su instalación. Esta capa solo se vuelve a construir si cambia requirements-local.txt.
RUN pip install -r requirements-local.txt
# Lógica de negocio compartida (la misma capa que usan las Lambdas).
COPY layers/common/ layers/common/
# Repositorios SQLite y simulador de los nodos ESP32.
COPY servidor_local/ servidor_local/
# Punto de entrada de la API.
COPY main.py .
# La app web compilada en la etapa 1; main.py la sirve en "/".
COPY --from=web /web/dist frontend/dist
# Usuario sin privilegios y carpeta para la base de datos (se puede montar como volumen).
RUN useradd --create-home --uid 10001 app && mkdir -p /datos && chown app /datos
# A partir de aquí el proceso no corre como root.
USER app
# Puerto en el que escucha la aplicación (documentación; el mapeo se hace con -p).
EXPOSE 8000
# Docker revisa cada 30 s que la API responda; si falla 3 veces marca el contenedor como "unhealthy".
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request as u; u.urlopen('http://127.0.0.1:%s/api/salud' % os.environ.get('PORT', '8000'), timeout=2)"]
# Proceso principal: uvicorn en 0.0.0.0 (todas las interfaces) y en el puerto de la variable PORT.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
