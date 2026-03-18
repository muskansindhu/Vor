# Vor (Verification of Off-platform Return)

Vor is named after the Norse goddess associated with wisdom and careful inquiry.
Here, Vor stands for **Verification of Off-platform Return**.

Think of Vor as a background investigator for field activity.
It watches incoming location signals, identifies meaningful stays, compares those stays against known bookings, and raises alerts when behavior looks like a potential off-platform revisit.

The project is intentionally split into small services so each responsibility is clean:
ingestion, processing, alerting, and traffic simulation for testing.

![Vor demo](assets/vor-demo.gif)

## What Runs Here

1. `gps-ingest-service`: accepts GPS pings and publishes them to Kafka.
2. `processing-service`: consumes pings, runs stay/risk logic, stores results in SQLite, and publishes suspicious-visit events.
3. `alert-service`: consumes suspicious-visit events and serves alerts via API.
4. `simulator-service`: keeps sending mixed payloads to exercise all flows continuously.

## Tech Stack

1. Language: `Python 3.11`
2. API framework: `FastAPI` (+ `Uvicorn`)
3. Messaging: `Apache Kafka` (Confluent Docker images)
4. Kafka client: `aiokafka`
5. Database: `SQLite`
6. ORM: `SQLAlchemy`
7. HTTP client (simulator): `httpx`
8. Containerization/orchestration: `Docker` + `Docker Compose`

## How The Story Flows

1. A ping hits `gps-ingest-service` at `POST /locations`.
2. The ping is validated and pushed to Kafka (`gps-pings` topic).
3. `processing-service` consumes that event and updates stay/risk state.
4. If a suspicious revisit is detected, processing writes to SQLite and publishes an alert event to `suspicious-visits`.
5. `alert-service` consumes those events and exposes them through `GET /alerts`.

## Main Endpoints

1. `POST /locations` (`gps-ingest-service`)
2. `POST /pings` (`processing-service`, optional direct/manual testing path)
3. `GET /alerts` (`alert-service`)
4. `GET /health` (all services)

## Kafka Variables

1. `KAFKA_BOOTSTRAP_SERVERS` (default: `localhost:9092`)
2. `KAFKA_PINGS_TOPIC` (default: `gps-pings`)
3. `KAFKA_CONSUMER_GROUP` (default: `vor-processing`, used by `processing-service`)
4. `KAFKA_ALERTS_TOPIC` (default: `suspicious-visits`)
5. `KAFKA_ALERTS_CONSUMER_GROUP` (default: `vor-alert-service`, used by `alert-service`)

## Run Everything

1. Start:

```bash
docker compose up --build
```

2. Stop:

```bash
docker compose down
```

## Simulator Notes

1. `simulator-service` starts automatically.
2. It keeps producing varied traffic until containers are stopped.
3. It includes invalid payloads, normal stays, spoofing/gap scenarios, and suspicious revisit candidates.
