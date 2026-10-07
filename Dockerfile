FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Приложение и конфигурация
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY config/ ./config/
COPY migrations/ ./migrations/
COPY alembic.ini ./
COPY templates/ ./templates/
COPY static/ ./static/
COPY examples/ ./examples/
COPY docker/entrypoint.sh ./docker/entrypoint.sh

RUN sed -i 's/\r$//' /app/docker/entrypoint.sh \
    && chmod +x /app/docker/entrypoint.sh \
    && mkdir -p /app/data /app/media /app/models /app/output /app/profiles

ENV HOST=0.0.0.0
ENV PORT=7777
ENV TF_CPP_MIN_LOG_LEVEL=3
ENV PYTHONUNBUFFERED=1

EXPOSE 7777

VOLUME ["/app/data", "/app/media", "/app/models", "/app/output"]

ENTRYPOINT ["/app/docker/entrypoint.sh"]
