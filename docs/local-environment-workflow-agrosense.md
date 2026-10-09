# Local Environment Startup and Teardown Workflow Specification

*AgroSense Café · Multi-Container Docker Compose Stack (Deliverables
E-02, E-04 \| CT-01, CT-02, CT-06)*

|                                                                         |
|:------------------------------------------------------------------------|
| \*\*Document Scope & Alignment:\\                                       |
| \*\*This document defines the standardized developer workflow for       |
| orchestrating the multi-container local stack of AgroSense Café via     |
| Docker Compose. It satisfies Deliverable E-04 and Jira Tasks AGRO-05A / |
| AGRO-05B, ensuring full alignment with Cross-Cutting Criteria CT-01     |
| (single-command startup, \<30 min onboarding), CT-02 (zero hardcoded    |
| secrets), and CT-06 (idempotent seed population).                       |


## 1. Overview & Developer Prerequisites

To ensure frictionless onboarding and strict parity between local
development and AWS cloud deployments, the entire AgroSense Café
stack—comprising PostgreSQL with PostGIS, RabbitMQ, Redis, Apache
Airflow, FastAPI, and data seeders—is containerized. Developers must
meet the following baseline environment prerequisites before executing
the workflow:

- **Docker Engine & Docker Compose v2:** Docker Desktop (macOS/Windows)
  or Docker Engine v24+ with compose plugin on Linux.

- **Environment Variables Configuration (.env):** A local .env file
  generated from .env.example containing non-sensitive credentials and
  service ports.

- **Resource Allocation:** Minimum 8 GB RAM and 4 CPUs assigned to the
  Docker daemon to handle Airflow, Spark, and PostgreSQL concurrently.

## 2. Local Stack Startup Workflow

In compliance with Criterion CT-01, bringing up the entire local
multi-container environment requires executing a single command from the
project root. The startup sequence automatically resolves service
dependencies, performs health checks, runs database migrations, and
triggers data seeding.

### 2.1 Primary Startup Command

|                                              |
|:---------------------------------------------|
| docker compose --env-file .env up -d --build |


### 2.2 Container Startup Dependency & Initialization Sequence

Docker Compose enforces strict startup ordering using condition-based
health checks (depends_on with service_healthy) to prevent race
conditions during database schema initialization:

1.  **Stage 1: Core Infrastructure Services:** PostgreSQL (PostGIS) and
    RabbitMQ containers launch first. PostgreSQL initializes the SRID
    4326 spatial extension, while RabbitMQ configures queues and
    exchange bindings.

2.  **Stage 2: Healthcheck Validation:** PostgreSQL executes pg_isready
    -U agrosense_user, and RabbitMQ runs rabbitmq-diagnostics ping.
    Upstream services wait until health status reaches 'healthy'.

3.  **Stage 3: Database Migrations & Seed Trigger:** An ephemeral init
    container executes Alembic database migrations followed by python
    scripts/seed/run_seed.py --mode dev --seed 42, populating 50 farms
    and simulated IoT data idempotently (CT-06).

4.  **Stage 4: Application & Orchestration Services:** FastAPI (web
    API), Airflow Webserver/Scheduler (Celery executor), and IoT
    Simulators start once database schema and seed data are verified.

## 3. Local Stack Teardown & Volume Management

Developers can stop or reset the local environment using standard Docker
Compose teardown commands. Care must be taken regarding persistent
volumes to distinguish between routine service stops and complete data
resets.

### 3.1 Routine Teardown (Preserving Data & State)

To temporarily halt execution without losing database records, RabbitMQ
queue state, or Airflow metadata, execute:

|                     |
|:--------------------|
| docker compose down |


### 3.2 Full Environment Reset (Destroying Named Volumes)

When testing schema migrations from scratch, re-running seed scripts, or
clearing corrupted queue states, developers must remove persistent named
volumes using the -v flag:

|                                         |
|:----------------------------------------|
| docker compose down -v --remove-orphans |


|                                                                       |
|:----------------------------------------------------------------------|
| \*\*⚠️ WARNING — PERSISTENT VOLUME PURGE:\\                           |
| \*\*Executing 'docker compose down -v' completely deletes the local   |
| PostgreSQL data volume (postgres_data), RabbitMQ queue volume         |
| (rabbitmq_data), and S3 local emulator buckets. Upon the next 'docker |
| compose up', the seed script will re-run automatically to reconstruct |
| the baseline state.                                                   |


## 4. Developer Commands Reference Table

The following reference table summarizes standard commands for local
environment lifecycle management:

| **Command**                                                   | **Primary Action / Purpose**                          | **Expected Output / Health Status**                |
|:--------------------------------------------------------------|:------------------------------------------------------|:---------------------------------------------------|
| docker compose up -d --build                                  | Builds images and starts all services in background   | All 7 containers reach 'healthy' / 'running' state |
| docker compose logs -f api                                    | Tail logs for FastAPI service in real time            | HTTP 200/201 request logs displayed in stdout      |
| docker compose exec db psql -U agrosense_user -d agrosense_db | Interactive PostgreSQL shell access                   | psql prompt ready; PostGIS extension verified      |
| docker compose stop                                           | Pauses all running containers without destroying them | Containers stopped; volumes & data preserved       |
| docker compose down -v                                        | Stops containers & permanently removes all volumes    | Volumes purged; environment clean for fresh build  |

## 5. Verification & Onboarding Checklist (CT-01)

To satisfy Criterion CT-01, an external team member must be able to
complete local environment setup and verify system operation in under 30
minutes following this checklist:

- **Repository Clone & Secret Verification:** Repository cloned locally;
  .env file created from .env.example with no hardcoded production keys
  (CT-02).

- **Single-Command Execution:** Executed 'docker compose up -d --build'
  without manual intervention or configuration errors.

- **Service Accessibility Verification:** FastAPI Swagger UI accessible
  at http://localhost:8000/docs; Airflow UI accessible at
  http://localhost:8080.

- **Seed Verification Query:** Executed 'SELECT COUNT(\*) FROM finca;'
  returning exactly 50 records in development mode (CT-06).

- **Teardown Validation:** Executed 'docker compose down -v' and
  confirmed complete cleanup of local resources.
