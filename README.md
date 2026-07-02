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

# Author

**Supplier Failure Radar Backend**

Machine Learning powered supplier risk prediction system for airline B2B operations.