FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.32.0" \
    "pydantic-settings>=2.6.0" \
    "email-validator>=2.2.0" \
    "asyncpg>=0.30.0" \
    "sqlalchemy>=2.0.36" \
    "alembic>=1.14.0" \
    "greenlet>=3.1.0" \
    "redis>=5.2.0" \
    "boto3>=1.35.0" \
    "python-json-logger>=2.0.7" \
    "python-multipart>=0.0.17" \
    "openpyxl>=3.1.5"

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
