FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir "redis>=5.2.0" "httpx>=0.28.0"

COPY main.py ./main.py

CMD ["python", "main.py"]
