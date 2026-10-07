# AgroSense Café — Local Docker Compose Service Blueprint

*Technical Specification for Local Multi-Container Stack (PostgreSQL,
PgAdmin, FastAPI, RabbitMQ, LocalStack)*

## 1. Executive Overview & Local Infrastructure Objectives

The local development and testing environment for **AgroSense Café** is
orchestrated using Docker Compose to replicate production cloud
capabilities locally. This containerized stack provides seamless offline
development, deterministic integration testing, and rapid local
validation without incurring AWS infrastructure costs. The stack
encapsulates five core services: PostgreSQL 15, PgAdmin 4, RabbitMQ
3.12, LocalStack (AWS S3 mock), and the FastAPI operational application
server.

To eliminate initialization race conditions—such as the API attempting
database migrations before PostgreSQL is accepting connections—the stack
relies on explicit healthchecks and conditional dependency trees
(depends_on.condition: service_healthy). All container communication
occurs over a dedicated, isolated bridge network (agrosense_network),
ensuring strict network isolation and service name resolution.

## 2. Containerized Service Blueprint Matrix

The following matrix summarizes the official base images, networking
rules, volume mounts, and operational roles for all containers in the
local AgroSense stack:
| **Service Name** | **Base Image & Tag** | **Exposed Ports** | **Persistent Volume** | **Operational Role** |
| --- | --- | --- | --- | --- |
| postgres | postgres:15-alpine | 5432:5432 | postgres\_data | Serving & Operational Database (PostgreSQL) |
| pgadmin | dpage/pgadmin4:latest | 5050:80 | pgadmin\_data | Database Web UI Management Console |
| rabbitmq | rabbitmq:3.12-management-alpine | 5672:5672  15672:15672 | rabbitmq\_data | AMQP Message Broker & Management UI |
| localstack | localstack/localstack:latest | 4566:4566 | localstack\_data | Mock AWS S3 Object Storage Data Lake |
| fastapi | python:3.11-slim (Custom) | 8000:8000 | None (Bind mount) | Operational REST API for Traceability & IoT |


## 3. Detailed Container Specifications & Healthcheck Configurations

### 3.1 Primary Operational Database — PostgreSQL 15 Alpine

The core relational datastore uses the lightweight postgres:15-alpine
official image. It stores operational farm records, producer metadata,
sensor registration, soil analysis, and supply chain traceability
contracts. It exposes standard port 5432 and persists data in named
volume postgres_data.

> **• Healthcheck Command:** pg_isready -U agrosense_user -d
> agrosense_db  
> **• Interval & Timeout:** Interval: 5s, Timeout: 5s, Retries: 5, Start
> Period: 10s.  
> **• Environment Variables:** POSTGRES_DB=agrosense_db,
> POSTGRES_USER=agrosense_user,
> POSTGRES_PASSWORD=agrosense_secure_pass_2026

### 3.2 Database Management UI — PgAdmin 4

Provides a web-based administration dashboard for developers and
database administrators to inspect tables, execute manual SQL queries,
and monitor database performance. Bound to host port 5050 (mapped to
internal port 80).

> **• Startup Dependency:** depends_on postgres with condition
> service_healthy.  
> **• Environment Variables:** PGADMIN_DEFAULT_EMAIL=admin@agrosense.co,
> PGADMIN_DEFAULT_PASSWORD=admin_secret_pass

### 3.3 Asynchronous Message Broker — RabbitMQ 3.12 Management

Manages asynchronous message queues for telemetry ingestion and delayed
cellular sync blocks. Uses rabbitmq:3.12-management-alpine to provide
both the AMQP message broker protocol on port 5672 and the web
management plugin on port 15672.

> **• Healthcheck Command:** rabbitmq-diagnostics -q ping  
> **• Interval & Timeout:** Interval: 10s, Timeout: 5s, Retries: 5,
> Start Period: 15s.  
> **• Environment Variables:** RABBITMQ_DEFAULT_USER=agrosense_mq,
> RABBITMQ_DEFAULT_PASS=mq_secure_pass_2026

### 3.4 Mock Cloud Storage Data Lake — LocalStack S3

Simulates AWS S3 locally, enabling Medallion Data Lake architecture
processing (Bronze raw telemetry, Silver cleaned data, Gold analytics)
without external AWS credentials or cloud billing. Exposes edge port
4566.

> **• Healthcheck Command:** curl -s
> http://localhost:4566/\_localstack/health \| grep -q '"s3":
> "running"'  
> **• Environment Variables:** SERVICES=s3,
> AWS_DEFAULT_REGION=us-east-1, DOCKER_HOST=unix:///var/run/docker.sock

### 3.5 Application REST API Server — FastAPI

The core operational backend developed in Python 3.11 with FastAPI. It
handles REST endpoints for buyer traceability queries, farm
registration, and IoT ingestion. Exposes port 8000 and depends strictly
on the health of PostgreSQL, RabbitMQ, and LocalStack.

> **• Healthcheck Command:** curl -f http://localhost:8000/health \|\|
> exit 1  
> **• Dependencies:** depends_on: postgres (service_healthy), rabbitmq
> (service_healthy), localstack (service_healthy).

## 4. Startup Order & Topological Dependency Resolution

The execution pipeline follows a strict multi-tier startup sequence to
ensure that infrastructural dependencies reach fully operational status
before dependent application code is executed:

> **• Tier 1 — Core Infrastructure (Parallel Initialization):**
> PostgreSQL, RabbitMQ, and LocalStack containers start simultaneously.
> Healthcheck probing begins according to individual start periods.
>
> **• Tier 2 — Infrastructure Readiness Probing:** Healthcheck commands
> evaluate service availability (\`pg_isready\`,
> \`rabbitmq-diagnostics\`, and \`LocalStack health\`). Containers
> transition from starting to healthy status.
>
> **• Tier 3 — Secondary Tooling & Application Startup:** PgAdmin starts
> once PostgreSQL is healthy. FastAPI backend container starts only
> after PostgreSQL, RabbitMQ, and LocalStack report healthy status.
>
> **• Tier 4 — Database Migration & Seed Ingestion:** FastAPI executes
> database Alembic migrations and triggers the seed engine script
> (\`python -m seed.runner\`) automatically upon validated DB
> connection.

## 5. Complete Production-Grade docker-compose.yml Reference

Below is the fully functional, copy-paste ready docker-compose.yml
manifest defining the local containerized infrastructure for AgroSense
Café:
|                                                                                     |
|:------------------------------------------------------------------------------------|
| version: '3.8'\\                                                                    |
| \\                                                                                  |
| networks:\\                                                                         |
| agrosense_network:\\                                                                |
| driver: bridge\\                                                                    |
| name: agrosense_network\\                                                           |
| \\                                                                                  |
| volumes:\\                                                                          |
| postgres_data:\\                                                                    |
| name: agrosense_postgres_data\\                                                     |
| pgadmin_data:\\                                                                     |
| name: agrosense_pgadmin_data\\                                                      |
| rabbitmq_data:\\                                                                    |
| name: agrosense_rabbitmq_data\\                                                     |
| localstack_data:\\                                                                  |
| name: agrosense_localstack_data\\                                                   |
| \\                                                                                  |
| services:\\                                                                         |
| postgres:\\                                                                         |
| image: postgres:15-alpine\\                                                         |
| container_name: agrosense_postgres\\                                                |
| restart: unless-stopped\\                                                           |
| ports:\\                                                                            |
| \- "5432:5432"\\                                                                    |
| environment:\\                                                                      |
| POSTGRES_DB: agrosense_db\\                                                         |
| POSTGRES_USER: agrosense_user\\                                                     |
| POSTGRES_PASSWORD: agrosense_secure_pass_2026\\                                     |
| volumes:\\                                                                          |
| \- postgres_data:/var/lib/postgresql/data\\                                         |
| networks:\\                                                                         |
| \- agrosense_network\\                                                              |
| healthcheck:\\                                                                      |
| test: \["CMD-SHELL", "pg_isready -U agrosense_user -d agrosense_db"\]\\             |
| interval: 5s\\                                                                      |
| timeout: 5s\\                                                                       |
| retries: 5\\                                                                        |
| start_period: 10s\\                                                                 |
| \\                                                                                  |
| pgadmin:\\                                                                          |
| image: dpage/pgadmin4:latest\\                                                      |
| container_name: agrosense_pgadmin\\                                                 |
| restart: unless-stopped\\                                                           |
| ports:\\                                                                            |
| \- "5050:80"\\                                                                      |
| environment:\\                                                                      |
| PGADMIN_DEFAULT_EMAIL: admin@agrosense.co\\                                         |
| PGADMIN_DEFAULT_PASSWORD: admin_secret_pass\\                                       |
| volumes:\\                                                                          |
| \- pgadmin_data:/var/lib/pgadmin\\                                                  |
| networks:\\                                                                         |
| \- agrosense_network\\                                                              |
| depends_on:\\                                                                       |
| postgres:\\                                                                         |
| condition: service_healthy\\                                                        |
| \\                                                                                  |
| rabbitmq:\\                                                                         |
| image: rabbitmq:3.12-management-alpine\\                                            |
| container_name: agrosense_rabbitmq\\                                                |
| restart: unless-stopped\\                                                           |
| ports:\\                                                                            |
| \- "5672:5672"\\                                                                    |
| \- "15672:15672"\\                                                                  |
| environment:\\                                                                      |
| RABBITMQ_DEFAULT_USER: agrosense_mq\\                                               |
| RABBITMQ_DEFAULT_PASS: mq_secure_pass_2026\\                                        |
| volumes:\\                                                                          |
| \- rabbitmq_data:/var/lib/rabbitmq\\                                                |
| networks:\\                                                                         |
| \- agrosense_network\\                                                              |
| healthcheck:\\                                                                      |
| test: \["CMD", "rabbitmq-diagnostics", "-q", "ping"\]\\                             |
| interval: 10s\\                                                                     |
| timeout: 5s\\                                                                       |
| retries: 5\\                                                                        |
| start_period: 15s\\                                                                 |
| \\                                                                                  |
| localstack:\\                                                                       |
| image: localstack/localstack:latest\\                                               |
| container_name: agrosense_localstack\\                                              |
| restart: unless-stopped\\                                                           |
| ports:\\                                                                            |
| \- "4566:4566"\\                                                                    |
| environment:\\                                                                      |
| \- SERVICES=s3\\                                                                    |
| \- AWS_DEFAULT_REGION=us-east-1\\                                                   |
| \- DOCKER_HOST=unix:///var/run/docker.sock\\                                        |
| volumes:\\                                                                          |
| \- localstack_data:/var/lib/localstack\\                                            |
| \- "/var/run/docker.sock:/var/run/docker.sock"\\                                    |
| networks:\\                                                                         |
| \- agrosense_network\\                                                              |
| healthcheck:\\                                                                      |
| test: \["CMD-SHELL", "curl -s http://localhost:4566/\_localstack/health \| grep     |
| -q '"s3": "running"' \|\| exit 1"\]\\                                               |
| interval: 10s\\                                                                     |
| timeout: 5s\\                                                                       |
| retries: 5\\                                                                        |
| start_period: 15s\\                                                                 |
| \\                                                                                  |
| fastapi:\\                                                                          |
| build:\\                                                                            |
| context: .\\                                                                        |
| dockerfile: Dockerfile\\                                                            |
| container_name: agrosense_fastapi\\                                                 |
| restart: unless-stopped\\                                                           |
| ports:\\                                                                            |
| \- "8000:8000"\\                                                                    |
| environment:\\                                                                      |
| DATABASE_URL:                                                                       |
| postgresql://agrosense_user:agrosense_secure_pass_2026@postgres:5432/agrosense_db\\ |
| RABBITMQ_URL: amqp://agrosense_mq:mq_secure_pass_2026@rabbitmq:5672/\\              |
| S3_ENDPOINT_URL: http://localstack:4566\\                                           |
| AWS_DEFAULT_REGION: us-east-1\\                                                     |
| AWS_ACCESS_KEY_ID: mock_key\\                                                       |
| AWS_SECRET_ACCESS_KEY: mock_secret\\                                                |
| networks:\\                                                                         |
| \- agrosense_network\\                                                              |
| depends_on:\\                                                                       |
| postgres:\\                                                                         |
| condition: service_healthy\\                                                        |
| rabbitmq:\\                                                                         |
| condition: service_healthy\\                                                        |
| localstack:\\                                                                       |
| condition: service_healthy\\                                                        |
| healthcheck:\\                                                                      |
| test: \["CMD-SHELL", "curl -f http://localhost:8000/health \|\| exit 1"\]\\         |
| interval: 10s\\                                                                     |
| timeout: 5s\\                                                                       |
| retries: 3\\                                                                        |
| start_period: 10s                                                                   |

