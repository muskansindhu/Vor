FROM python:3.11-slim

WORKDIR /app
COPY location-simulator-service /app/service

RUN pip install --no-cache-dir -r /app/service/requirements.txt

CMD ["python", "/app/service/main.py"]
