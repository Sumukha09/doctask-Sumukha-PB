FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install build deps needed by some wheels (psycopg binary is fine, but keep
# the toolchain available so any future pure-Python fallback compiles).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first for better layer caching.
COPY pyproject.toml ./
RUN pip install --upgrade pip \
    && pip install .[dev]

# Copy application code.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY tests ./tests

EXPOSE 8000

# Default command runs the API; docker-compose overrides this when needed.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
