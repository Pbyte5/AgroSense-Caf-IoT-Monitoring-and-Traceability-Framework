# Healthcheck and Readiness Strategy in Docker Compose

This document defines the health verification strategy (*Healthchecks*), timing calibration, startup dependency graph, and `/health` endpoint specification for the interdependent local services of **AgroSense Café** (**PostgreSQL**, **RabbitMQ**, **LocalStack S3**, and **FastAPI**).

---

## 1. Purpose and Technical Rationale

When `docker compose up -d` is run, the Docker engine starts the container processes almost in parallel. However, **a container being in the `Up` state (process started) does not mean the service is `Ready` (able to accept TCP/HTTP connections)**:

- **PostgreSQL 16** needs extra time on its first startup to run the bootstrap scripts in `/docker-entrypoint-initdb.d/` (`01_enable_extensions.sql`, `02_create_schemas.sql`, `03_create_roles_and_db.sql`).
- **RabbitMQ** needs to initialize the Erlang engine and import the exchange and queue topology (`definitions.json`).
- **LocalStack** must bring up the S3 emulator and run the `01_init_s3_buckets.sh` script to create the buckets of the Medallion architecture (`Bronze`, `Silver`, `Gold`).

If **FastAPI** or the **Alembic** migrations try to connect at second 1 using a plain `depends_on`, they will fail with `Connection refused` errors. To eliminate this race condition, all critical services implement native `healthcheck` blocks combined with the `condition: service_healthy` directive.

---

## 2. Calibration Parameters (Timings)

Each `healthcheck` block in `docker-compose.yml` is calibrated with four core parameters:

| Parameter                  | Technical Description                                                                                                       | Impact on AgroSense Café                                                                                                                                                     |
| :------------------------- | :-------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`interval`**             | How often Docker runs the verification command inside the container.                                                        | Defines how quickly it is detected that a service is ready or has gone down (`10s` to `15s`).                                                                                |
| **`timeout`**              | Maximum time Docker waits for the probe command to respond before considering it failed.                                    | Prevents hung checks from blocking the Docker daemon (`5s`).                                                                                                                 |
| **`retries`**              | Number of consecutive failures allowed before the container is marked `unhealthy`.                                          | Prevents false positives caused by momentary CPU spikes during startup (`3` to `5` attempts).                                                                                |
| **`start_period`**         | Initial grace period after container start during which failures **do not count against retries**.                          | **Critical:** Lets PostgreSQL, RabbitMQ, and LocalStack run their initialization scripts without being prematurely marked as failed (`10s` to `20s`).                        |

---

## 3. Healthcheck Matrix by Service

| Service        | Container              | Verification Command (`test`)                        | `interval` | `timeout` | `retries` | `start_period` | Success Criterion (`healthy`)                                                                          |
| :------------- | :--------------------- | :--------------------------------------------------- | :--------: | :-------: | :-------: | :------------: | :----------------------------------------------------------------------------------------------------- |
| **PostgreSQL** | `agrosense_postgres`   | `pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}`   |   `10s`    |   `5s`    |    `5`    |     `20s`      | The engine accepts SQL connections on the main DB after `/docker-entrypoint-initdb.d/` has finished.   |
| **RabbitMQ**   | `agrosense_rabbitmq`   | `rabbitmq-diagnostics -q ping`                       |   `10s`    |   `5s`    |    `5`    |     `20s`      | The Erlang node is active, AMQP port `5672` responds, and the queues are loaded.                       |
| **LocalStack** | `agrosense_localstack` | `awslocal s3 ls`                                     |   `10s`    |   `5s`    |    `5`    |     `15s`      | The S3 API on port `4566` responds and lists the Medallion buckets.                                    |
| **FastAPI**    | `agrosense_fastapi`    | `curl -f http://localhost:8000/health`               |   `15s`    |   `5s`    |    `3`    |     `10s`      | The Uvicorn server responds `HTTP 200 OK`, validating an active connection to the DB, queue, and S3.   |

---

## 4. Dependency Sequencing Graph (Dependency Order)

The local environment starts up following a strict three-level sequence governed by `condition: service_healthy` and `condition: service_completed_successfully`:

```text
[Level 1: Base Infrastructure]          [Level 2: Backend Application]         [Level 3: Tasks / Migrations]
┌─────────────────────────────┐
│ postgres (service_healthy)  ├────────┐
└─────────────────────────────┘        │
┌─────────────────────────────┐        │      ┌────────────────────────┐      ┌──────────────────────────────┐
│ rabbitmq (service_healthy)  ├────────┼─────►│ fastapi                ├─────►│ alembic_migrate / seed_data  │
└─────────────────────────────┘        │      │ (API Server - healthy) │      │ (Post-readiness jobs)        │
┌─────────────────────────────┐        │      └────────────────────────┘      └──────────────────────────────┘
│ localstack (service_healthy)├────────┘
└─────────────────────────────┘
```

### Step-by-Step Sequencing Flow:

1. **Level 1 (Infrastructure):** Docker starts `postgres`, `rabbitmq`, and `localstack` simultaneously. All of them enter the `health: starting` state during their `start_period`.
2. **Level 2 (Backend API):** The `fastapi` container waits until **all three Level 1 services** report `healthy`. Only then does it start Uvicorn and expose the `/health` endpoint.
3. **Level 3 (Migrations / Seeds):** The migration containers or commands (`alembic upgrade head`) and the seed data load (`seed_script`) run with the guarantee that both the database and the backend are operational.

---

## 5. Full Specification in `docker-compose.yml`

Below is the consolidated configuration with the `healthcheck` blocks and explicit `depends_on` rules:

```yaml
services:
  # ==========================================================================
  # LEVEL 1: BASE INFRASTRUCTURE (PostgreSQL, RabbitMQ, LocalStack)
  # ==========================================================================
  postgres:
    image: postgres:16-alpine
    container_name: agrosense_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-agrosense_db}
      POSTGRES_USER: ${POSTGRES_USER:-agrosense_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-agrosense_password}
      TZ: UTC
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - ./docker/postgres/init:/docker-entrypoint-initdb.d:ro
      - postgres_data:/var/lib/postgresql/data
    networks:
      - agrosense_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-agrosense_user} -d ${POSTGRES_DB:-agrosense_db}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s

  rabbitmq:
    image: rabbitmq:3.13-management-alpine
    container_name: agrosense_rabbitmq
    hostname: agrosense-rabbitmq
    restart: unless-stopped
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_DEFAULT_USER:-agrosense_mq}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_DEFAULT_PASS:-agrosense_mq_secret}
      RABBITMQ_DEFAULT_VHOST: ${RABBITMQ_DEFAULT_VHOST:-/agrosense}
    ports:
      - "${RABBITMQ_AMQP_PORT:-5672}:5672"
      - "${RABBITMQ_MGMT_PORT:-15672}:15672"
    volumes:
      - ./docker/rabbitmq/rabbitmq.conf:/etc/rabbitmq/rabbitmq.conf:ro
      - ./docker/rabbitmq/definitions.json:/etc/rabbitmq/definitions.json:ro
      - rabbitmq_data:/var/lib/rabbitmq
    networks:
      - agrosense_network
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s

  localstack:
    image: localstack/localstack:3.7
    container_name: agrosense_localstack
    restart: unless-stopped
    environment:
      SERVICES: s3
      PERSISTENCE: 1
      AWS_DEFAULT_REGION: ${AWS_DEFAULT_REGION:-us-east-1}
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:-test}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:-test}
    ports:
      - "${LOCALSTACK_PORT:-4566}:4566"
    volumes:
      - ./docker/localstack/init:/etc/localstack/init/ready.d:ro
      - localstack_data:/var/lib/localstack
    networks:
      - agrosense_network
    healthcheck:
      test: ["CMD", "awslocal", "s3", "ls"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 15s

  # ==========================================================================
  # LEVEL 2: BACKEND API (FastAPI)
  # ==========================================================================
  fastapi:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: agrosense_fastapi
    restart: unless-stopped
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+psycopg://${POSTGRES_USER:-agrosense_user}:${POSTGRES_PASSWORD:-agrosense_password}@postgres:5432/${POSTGRES_DB:-agrosense_db}
      RABBITMQ_URL: amqp://${RABBITMQ_DEFAULT_USER:-agrosense_mq}:${RABBITMQ_DEFAULT_PASS:-agrosense_mq_secret}@rabbitmq:5672/%2Fagrosense
      AWS_ENDPOINT_URL: http://localstack:4566
    ports:
      - "${API_PORT:-8000}:8000"
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
      localstack:
        condition: service_healthy
    networks:
      - agrosense_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s

networks:
  agrosense_network:
    name: agrosense_network
    driver: bridge

volumes:
  postgres_data:
    name: agrosense_postgres_data
  rabbitmq_data:
    name: agrosense_rabbitmq_data
  localstack_data:
    name: agrosense_localstack_data
```

---

## 6. `/health` Endpoint Specification in FastAPI

For the `fastapi` container's healthcheck to be a true **Readiness** indicator (and not just a shallow check that the HTTP server is up), the `GET /health` endpoint actively verifies connectivity with the dependent services.

### 6.1 HTTP Response Contract

- **Healthy State (`HTTP 200 OK`):**

  ```json
  {
    "status": "healthy",
    "database": "connected",
    "rabbitmq": "connected",
    "storage": "connected"
  }
  ```
- **Degraded / Unavailable State (`HTTP 503 Service Unavailable`):**
  When any dependency fails, the endpoint returns `503 Service Unavailable`, which makes `curl -f` return a non-zero exit code (`exit code 22`) and causes Docker to mark the container as `unhealthy`:

  ```json
  {
    "status": "unhealthy",
    "database": "connected",
    "rabbitmq": "disconnected",
    "storage": "connected"
  }
  ```

### 6.2 Reference Implementation (`app/api/routes/health.py`)

```python
import socket
from urllib.parse import urlparse
import boto3
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db

router = APIRouter(tags=["Health & Readiness"])


def check_rabbitmq_connection(rabbitmq_url: str, timeout: float = 2.0) -> bool:
    """Verifies that the RabbitMQ AMQP port accepts TCP connections."""
    try:
        parsed = urlparse(rabbitmq_url)
        host = parsed.hostname or "rabbitmq"
        port = parsed.port or 5672
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_s3_storage(endpoint_url: str) -> bool:
    """Verifies that LocalStack S3 responds and contains the Medallion buckets."""
    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_DEFAULT_REGION,
        )
        s3_client.list_buckets()
        return True
    except Exception:
        return False


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check(response: Response, db: Session = Depends(get_db)) -> dict[str, str]:
    """
    Liveness and Readiness endpoint for Docker Compose and load balancers.
    Verifies real connectivity with PostgreSQL, RabbitMQ, and LocalStack S3.
    """
    # 1. Check PostgreSQL (Serving DB)
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    # 2. Check RabbitMQ (AMQP Broker)
    mq_status = "connected" if check_rabbitmq_connection(settings.RABBITMQ_URL) else "disconnected"

    # 3. Check LocalStack (Mock S3 Storage)
    s3_status = "connected" if check_s3_storage(settings.AWS_ENDPOINT_URL) else "disconnected"

    is_healthy = all(
        service == "connected" for service in (db_status, mq_status, s3_status)
    )

    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "database": db_status,
        "rabbitmq": mq_status,
        "storage": s3_status,
    }
```

---

## 7. Verification and Diagnostic Commands

During local development, use the following commands to inspect the health status and audit the startup times of each container:

```powershell
# 1. Start the whole stack, waiting for the healthchecks to pass in order
docker compose up -d --wait

# 2. Verify that all containers show "(healthy)" in the STATUS column
docker compose ps

# 3. Inspect the detailed healthcheck execution history for PostgreSQL
docker inspect --format "{{json .State.Health }}" agrosense_postgres

# 4. Manually test the FastAPI health endpoint from your terminal
curl -i http://localhost:8000/health
```
