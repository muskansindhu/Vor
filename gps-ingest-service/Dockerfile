FROM python:3.11-slim

WORKDIR /app
COPY shared /app/shared
COPY gps-ingest-service /app/service

RUN pip install --no-cache-dir -r /app/service/requirements.txt

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8000"]