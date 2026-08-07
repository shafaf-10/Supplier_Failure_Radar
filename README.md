# Supplier Failure Radar

Supplier Failure Radar is a machine learning-based backend system that predicts supplier risk, detects anomalies, and estimates future supplier failures for airline B2B booking operations.

---

# Project Overview

The system continuously analyzes booking transactions, supplier performance, search sessions, refund requests, credit requests, and wallet transactions to calculate supplier health.

It provides:

- Current supplier risk prediction
- Future supplier failure prediction
- Supplier anomaly detection
- Risk recommendations
- Cached prediction APIs
- Prometheus monitoring
- Scheduled ML pipeline execution

---

# Technology Stack

## Backend

- FastAPI
- Python 3.12
- SQLAlchemy
- MySQL
- Redis
- APScheduler

## Machine Learning

- Scikit-learn
- Random Forest
- Gradient Boosting
- Isolation Forest
- Pandas
- NumPy
- Joblib

## Monitoring

- Prometheus Client

---

# Project Structure

```
app/
│
├── api/
│
├── infra/
│
├── ml/
│
├── services/
│
├── middlewares/
│
├── observability/
│
├── security/
│
├── data_generation/
│
├── domain/
│
└── main.py
```

---

# Main Features

- Supplier Risk Prediction
- Future Failure Prediction
- Supplier Anomaly Detection
- Automatic Prediction Pipeline
- Redis Cache
- Prometheus Metrics
- Health Endpoint
- API Authentication
- Scheduler
- Streamlit Dashboard Support

---

# Machine Learning Models

## Risk Classification

Models evaluated:

- Random Forest
- Gradient Boosting

Best model is automatically selected.

---

## Future Failure Prediction

Predicts supplier instability for the next 7 days.

---

## Anomaly Detection

Isolation Forest detects abnormal supplier behaviour.

---

# Data Sources

The ML pipeline uses:

- Bookings
- Booking Processes
- Booking Flights
- Booking Passengers
- Refund Requests
- Credit Requests
- Search Sessions
- Wallet Transactions

---

# API Endpoints

## Health Check

```
GET /health
```

---

## Metrics

```
GET /metrics
```

---

## Supplier Predictions

```
GET /supplier-predictions
```

Parameters

```
period

all
24h
7d
30d
1y
```

---

## Refresh ML Pipeline

```
POST /refresh-model
```

---

# Authentication

All API endpoints require:

```
Header:

X-API-Key
```

Example

```
X-API-Key: dev-secret-key
```

---

# Running the Backend

Create virtual environment

```bash
python -m venv venv
```

Activate

Windows

```bash
venv\Scripts\activate
```

Install packages

```bash
pip install -r requirements.txt
```

Start FastAPI

```bash
python -m uvicorn app.main:app --reload --port 8000
```

---

# API Documentation

Swagger

```
http://127.0.0.1:8000/docs
```

ReDoc

```
http://127.0.0.1:8000/redoc
```

---

# Prometheus Metrics

```
http://127.0.0.1:8000/metrics
```

---

# Health Endpoint

```
http://127.0.0.1:8000/health
```

---

# Scheduler

The supplier prediction pipeline runs automatically every:

```
15 minutes
```

It:

- Generates supplier features
- Runs ML prediction
- Detects anomalies
- Updates Redis cache

---

# Caching

Redis is used for:

- Supplier predictions
- Dashboard responses
- Faster API performance

---

# Logging

Application logging is available for:

- API requests
- Scheduler
- Redis
- Errors
- ML training
- Data generation

---

# Security

Implemented:

- API Key Authentication
- Restricted CORS
- Rate Limiting
- Global Error Handling

---

# Monitoring

Prometheus metrics include:

- HTTP requests
- Request latency
- Error count

---

# Model Storage

Models are stored inside:

```
app/ml/models/
```

Latest models

- risk_model.pkl
- future_failure_model.pkl
- anomaly_model.pkl

Older model versions are automatically cleaned to prevent unlimited disk growth.

---

# Failure Attribution (Laravel ↔ Radar contract)

Not every failure logged in `bookings`, `booking_processes`, or `search_sessions`
is actually the supplier's fault — bugs in our own platform code (Laravel or
the radar itself) can also produce failure rows. The radar attributes every
failure to `SUPPLIER`, `INTERNAL`, `TIMEOUT`, or `UNKNOWN`, and excludes
`INTERNAL` failures from supplier risk scoring, ML features, training data,
and supplier alerts. `INTERNAL` failures are surfaced separately as a
Platform Incident instead.

## Migration (shared MySQL DB)

```sql
ALTER TABLE booking_processes
  ADD COLUMN failure_source VARCHAR(20) NULL,  -- SUPPLIER | INTERNAL | TIMEOUT | UNKNOWN
  ADD COLUMN error_code VARCHAR(100) NULL,
  ADD COLUMN latency_ms INT NULL;

ALTER TABLE search_sessions
  ADD COLUMN failure_source VARCHAR(20) NULL,
  ADD COLUMN error_code VARCHAR(100) NULL,
  ADD COLUMN latency_ms INT NULL;

ALTER TABLE bookings
  ADD COLUMN failure_source VARCHAR(20) NULL;  -- for FAILED/EXPIRED rows
```

The radar reads these columns automatically via its existing `SELECT *`
queries — no radar code change is needed once the migration is applied.

## Tagging rules (Laravel catch blocks)

| Condition | `failure_source` |
|---|---|
| Guzzle `ConnectException` / cURL timeout (code 28) / read timeout to supplier | `TIMEOUT` |
| Supplier HTTP client returned 4xx/5xx to a valid request | `SUPPLIER` |
| `QueryException`, `RedisException`, `ValidationException`, any uncaught `LogicException`/`Error`, own-endpoint 500 | `INTERNAL` |
| Anything else | `UNKNOWN` |

Also set `error_code` (exception class or supplier error code) and
`latency_ms` (request duration). Only `INTERNAL` is excluded from supplier
scoring — `SUPPLIER`, `TIMEOUT`, and `UNKNOWN` all still count toward
supplier risk.

## Fallback (untagged rows)

If a row has no `failure_source` (or an invalid value), the radar falls back
to its own inference, in order: a detected platform-incident window (many
suppliers failing at once) → `INTERNAL`; keyword matching on the row's error
text → `INTERNAL` or `SUPPLIER`; for `search_sessions`, whether every
supplier in that search failed together (`INTERNAL`) or only some
(`SUPPLIER`); otherwise `UNKNOWN`.

## Admin integration

The Laravel admin panel embeds or proxies the radar endpoints
(`GET /supplier-predictions`, `POST /refresh-model`) with the `X-API-Key`
header; the radar reads the same shared database.

# Author

**Supplier Failure Radar Backend**

Machine Learning powered supplier risk prediction system for airline B2B operations.