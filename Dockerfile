FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    DATABASE_URL=sqlite:////data/todo.db

WORKDIR /app

RUN addgroup --system app \
    && adduser --system --ingroup app app \
    && mkdir -p /data \
    && chown -R app:app /data

COPY requirements.txt ./

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY alembic.ini pyproject.toml ./
COPY app ./app
COPY migrations ./migrations

USER app

EXPOSE 8000

VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["sh", "-c", "test -n \"$JWT_SECRET_KEY\" || { echo 'JWT_SECRET_KEY is required'; exit 1; }; alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]