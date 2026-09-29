# python:3.12-slim, not 3.14: wheel coverage for psycopg[binary] and pydantic.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Requirements first so the layer caches across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The API imports pipeline.db, so both packages ship.
COPY api/ ./api/
COPY pipeline/ ./pipeline/
COPY crawler/ ./crawler/
# pipeline.migrate reads schema.sql and the migrations.
COPY db/ ./db/

EXPOSE 8000

# Shell form is load-bearing: Railway injects $PORT at runtime and the exec
# form would pass the literal string "${PORT:-8000}" to uvicorn. A failed
# migration stops the deploy rather than serving an old schema.
CMD python -m pipeline.migrate && uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
