# Reliable Webhook Delivery & Event Processing Platform

A full-stack backend engineering project designed to manage events and deliver webhook notifications reliably, with retry handling, failure tracking, and a monitoring dashboard.

Built with **FastAPI, Python, MySQL, SQLAlchemy, React, and Bootstrap**, the platform demonstrates core backend engineering concepts including REST API design, database integration, background processing, HTTP communication, and delivery lifecycle management.

## Overview

Webhooks allow applications to notify other systems when an event occurs. However, delivery can fail because of network issues, unavailable endpoints, or unsuccessful HTTP responses.

This project addresses these challenges by providing a centralized platform to register webhook endpoints, create events, manage delivery records, retry failed deliveries, and monitor delivery status through a web dashboard.

## Key Features

- **Webhook Management:** Register and retrieve webhook endpoints using REST APIs.
- **Event Management:** Create and store events with structured JSON payloads.
- **Delivery Tracking:** Maintain delivery records, HTTP response codes, attempt counts, and delivery statuses.
- **Retry Mechanism:** Retry eligible failed deliveries using configurable attempt limits and backoff delays.
- **Dead-Letter Handling:** Isolate deliveries that reach the retry limit or encounter configured permanent HTTP errors.
- **Manual Retry:** Requeue dead-letter deliveries directly from the dashboard.
- **Background Processing:** Process pending webhook deliveries through a worker and trigger individual deliveries through FastAPI background tasks.
- **Interactive Dashboard:** View webhooks, events, delivery activity, and delivery statuses through a React interface.
- **Persistent Storage:** Store webhook configurations, events, and delivery records in MySQL.

## Technology Stack

| Component | Technology |
|---|---|
| Backend API | Python, FastAPI |
| Database | MySQL |
| ORM | SQLAlchemy |
| Database Driver | PyMySQL |
| HTTP Client | HTTPX |
| Frontend | React, Vite |
| UI Framework | Bootstrap, React-Bootstrap |
| Testing | Pytest |
| API Documentation | Swagger UI / OpenAPI |

## Architecture

```text
                 ┌──────────────────────┐
                 │    React Dashboard   │
                 │  Webhooks / Events   │
                 │      Deliveries      │
                 └──────────┬───────────┘
                            │ REST API
                            ▼
                 ┌──────────────────────┐
                 │     FastAPI Backend  │
                 │  API and Validation  │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │    MySQL Database    │
                 │ Webhooks / Events /  │
                 │      Deliveries      │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │   Delivery Worker    │
                 │ HTTP POST / Retries  │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │  Registered Receiver │
                 │ HTTP Response / Logs │
                 └──────────────────────┘
```

The dashboard communicates with the FastAPI backend. The backend persists application data in MySQL, while delivery processing sends event payloads to registered endpoints and updates delivery records based on the result.

## Delivery Lifecycle

1. Register a destination URL as a webhook.
2. Create an event with an event type and JSON payload.
3. Create or associate delivery records for the relevant webhooks.
4. Process pending deliveries by sending HTTP POST requests to their destination URLs.
5. Record the HTTP response, attempt count, and delivery status.
6. Retry eligible failures according to the configured retry policy.
7. Move deliveries to the dead-letter state when retry limits or configured permanent-error rules apply.
8. Manually requeue dead-letter deliveries from the dashboard when needed.

## Retry Strategy

The delivery worker uses a configurable maximum attempt count and exponential-style backoff.

The current retry delay is calculated as:

\[
\text{Delay} = 5 \times 3^{(\text{attempts}-1)}
\]

This produces delays of 5, 15, and 45 seconds for successive attempts.

The worker also distinguishes between successful HTTP responses, configured permanent HTTP errors, retryable failures, and request exceptions.

Manual retries reset the current retry-cycle attempt count while preserving the lifetime `total_attempts` counter.

## Project Structure

```text
Webhook Platform/
├── app/
│   ├── api/
│   │   ├── webhooks.py
│   │   ├── events.py
│   │   └── deliveries.py
│   ├── core/
│   │   └── database.py
│   ├── models/
│   │   ├── webhook.py
│   │   ├── event.py
│   │   └── delivery.py
│   ├── schemas/
│   ├── services/
│   ├── workers/
│   │   └── delivery_worker.py
│   ├── main.py
│   └── test_receiver.py
├── frontend/
│   ├── src/
│   ├── package.json
│   └── ...
├── tests/
├── requirements.txt
├── .gitignore
└── README.md
```

*Note: Adjust the structure above if your actual repository uses different filenames or folders.*

## Getting Started

### Prerequisites

Install the following before running the project:

- Python 3.11 or later
- Node.js and npm
- MySQL Server and MySQL Workbench
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/reliable-webhook-platform.git
cd reliable-webhook-platform
```

Replace `YOUR-USERNAME` with your GitHub username.

### 2. Configure the Backend

Create and activate a virtual environment.

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the Python dependencies:

```powershell
pip install -r requirements.txt
```

Configure your MySQL connection using environment variables or your project's database configuration. Create a database named `webhook_platform` if the application expects that name.

**Security:** Never commit database passwords, `.env` files containing secrets, or production credentials. Keep a sanitized `.env.example` file if environment variables are required.

### 3. Start the Backend API

From the project root, run:

```powershell
python -m uvicorn app.main:app --reload --reload-dir app --port 8001
```

The backend will be available at:

- API base URL: `http://127.0.0.1:8001`
- Interactive API documentation: `http://127.0.0.1:8001/docs`
- Health check: `http://127.0.0.1:8001/health`

### 4. Start the Test Receiver

Open another terminal from the project root:

```powershell
python -m uvicorn app.test_receiver:app --host 127.0.0.1 --port 8002
```

The receiver exposes a successful endpoint at `/receive` and a test endpoint at `/receive-404` for simulating an HTTP 404 response.

### 5. Start the Frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the local Vite URL shown in the terminal, normally:

`http://localhost:5173`

### 6. Run the Delivery Worker

From a separate terminal at the project root:

```powershell
python -m app.workers.delivery_worker
```

The worker polls for eligible deliveries and processes them according to its configured retry policy.

**Development note:** The polling worker and API-triggered manual retry tasks can overlap if both process the same delivery concurrently. The current implementation should be treated as a development project until concurrent delivery claiming and idempotency are addressed.

## API Overview

The following endpoints are implemented in the project.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Check API health |
| `POST` | `/webhooks` | Register a webhook |
| `GET` | `/webhooks` | List webhooks |
| `GET` | `/webhooks/{id}` | Retrieve a webhook |
| `POST` | `/events` | Create an event |
| `GET` | `/events` | List events |
| `GET` | `/deliveries/` | List and filter deliveries |
| `POST` | `/deliveries/{id}/retry` | Requeue a dead-letter delivery |

Use the Swagger UI at `/docs` to inspect request schemas, send requests, and review responses.

## Testing

Run the automated backend test suite from the project root:

```powershell
python -m pytest
```

The test suite previously passed 17 tests during development. Run it against your current code before publishing and update this statement if the result changes.

The local test receiver can also be used to validate successful HTTP delivery and simulate permanent HTTP failures.

## Current Limitations

This project is intended for learning and portfolio demonstration. It is not yet a production-ready distributed delivery service.

Potential improvements include:

- Atomic delivery claiming and safe concurrent worker processing.
- Idempotency keys and duplicate-delivery protection.
- Authentication, authorization, and signed webhook requests.
- Structured logging, metrics, and delivery history.
- Database migrations and production deployment.
- Integration tests for retries, network failures, and concurrent execution.

## Learning Outcomes

This project demonstrates practical experience with:

- Designing RESTful APIs using FastAPI.
- Integrating MySQL with SQLAlchemy.
- Modeling related entities and delivery states.
- Sending HTTP requests and handling response failures.
- Implementing retry policies and backoff scheduling.
- Connecting a React dashboard to backend APIs.
- Debugging and validating an end-to-end delivery workflow.

## Future Enhancements

- Webhook signature verification.
- Configurable retry policies per endpoint.
- Delivery-detail pages and complete attempt history.
- Automated integration testing.
- Docker-based development and deployment.
- Production-grade queueing and observability.

## Author

**Udit Bansal**

- GitHub: [udit-create](https://github.com/udit-create)
- LinkedIn: [Udit Bansal](https://linkedin.com/in/udit-bansal-a5b002341)

---

*Built as a backend engineering and full-stack learning project.*
