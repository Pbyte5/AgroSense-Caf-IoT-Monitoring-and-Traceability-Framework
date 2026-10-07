# Docker Network Topology & Direct AWS S3 Integration Specification

AgroSense Café · Multi-Container Docker Compose Stack (Direct Amazon Web
Services Model)

# 1. Architectural Alignment: Direct Amazon S3 Cloud Integration

In direct alignment with the official AgroSense Café Cloud Architecture
diagram, the local development ecosystem interacts directly with
**Amazon S3 in AWS** for both the Medallion Data Lake and Database
Backup management. Local containers (FastAPI, Apache Airflow, and
PySpark ETL jobs) eliminate local emulation layers, utilizing the
official AWS SDK (boto3) and PySpark S3A connectors authenticated via
AWS environment credentials stored in the local **.env** file.

- **Data Lake Bucket (agrosense-datalake-prod):** Stores raw IoT
  telemetry, satellite climate metrics from NASA POWER/Open-Meteo, and
  curated Parquet tables across Bronze, Silver, and Gold layers.

- **Database Backups Bucket (agrosense-db-backups-prod):** Receives
  daily compressed pg_dump archives and WAL logs directly from the local
  PostgreSQL instance via cron execution.

# 2. Custom Bridge Network Isolation Topology (AWS VPC Subnet Model)

To replicate the AWS Virtual Private Cloud (VPC) multi-AZ network
perimeter locally, Docker Compose configures two custom user-defined
bridge networks:

- **agrosense_public_subnet (Ingress Tier):** Replicates the AWS Public
  Subnet. Connects public-facing endpoints including the FastAPI REST
  gateway (Swagger UI) and the Apache Airflow web management interface.

- **agrosense_private_subnet (Isolated Data Tier):** Replicates the AWS
  Private Subnet. Isolates core datastores and queue brokers
  (PostgreSQL/PostGIS, RabbitMQ, Redis) from direct external ingress,
  allowing access only from dual-homed application gateways.

## Table 1: Service-to-Network Attachment Matrix

| **Service Name**  | **Container Name**    | **Attached Network Subnets**  | **AWS Cloud Endpoint Target** |
|:------------------|:----------------------|:------------------------------|:------------------------------|
| api               | agrosense_api         | public_subnet, private_subnet | Amazon S3 (Data Lake)         |
| airflow_webserver | agrosense_airflow_web | public_subnet, private_subnet | Amazon S3 (Data Lake)         |
| db                | agrosense_db          | private_subnet                | S3 Backup Bucket (pg_dump)    |
| broker            | agrosense_broker      | private_subnet                | None (Internal IoT Queue)     |
| simulators        | agrosense_sim         | private_subnet                | RabbitMQ Broker               |

# 3. Local Persistent Named Volume Topology

With object storage offloaded directly to Amazon S3, local state
persistence is dedicated exclusively to relational data, message queues,
and execution logs:

- **pg_spatial_data (/var/lib/postgresql/data):** Stores PostgreSQL
  database tables, PostGIS spatial indices, farm boundary polygons
  (RN-09), and seed records (CT-06).

- **iot_telemetry_queue_data (/var/lib/rabbitmq):** Retains durable
  RabbitMQ queues holding offline telemetry bursts (up to 7 days of
  network disconnection tolerance, RNF-01).

- **airflow_logs_data (/opt/airflow/logs):** Preserves Airflow DAG run
  logs and ETL task execution histories for local debugging.

- **redis_data (/data):** Maintains Celery task broker cache for Airflow
  background workers.

# 4. Declarative Docker Compose Configuration (Direct AWS S3)

version: '3.8'  
  
networks:  
agrosense_public_subnet:  
driver: bridge  
name: agrosense_public_subnet  
agrosense_private_subnet:  
driver: bridge  
name: agrosense_private_subnet  
  
volumes:  
pg_spatial_data:  
driver: local  
iot_telemetry_queue_data:  
driver: local  
airflow_logs_data:  
driver: local  
redis_data:  
driver: local  
  
services:  
db:  
image: postgis/postgis:16-3.4-alpine  
container_name: agrosense_db  
environment:  
POSTGRES_USER: \${POSTGRES_USER:-agrosense_user}  
POSTGRES_PASSWORD: \${POSTGRES_PASSWORD:-change_this_locally}  
POSTGRES_DB: \${POSTGRES_DB:-agrosense_db}  
volumes:  
- pg_spatial_data:/var/lib/postgresql/data  
networks:  
- agrosense_private_subnet  
  
broker:  
image: rabbitmq:3.13-management-alpine  
container_name: agrosense_broker  
volumes:  
- iot_telemetry_queue_data:/var/lib/rabbitmq  
networks:  
- agrosense_private_subnet  
  
api:  
build: ./apps/api  
container_name: agrosense_api  
ports:  
- "8000:8000"  
environment:  
- POSTGRES_HOST=db  
- RABBITMQ_HOST=broker  
- AWS_ACCESS_KEY_ID=\${AWS_ACCESS_KEY_ID}  
- AWS_SECRET_ACCESS_KEY=\${AWS_SECRET_ACCESS_KEY}  
- AWS_DEFAULT_REGION=\${AWS_REGION:-us-east-1}  
- S3_DATALAKE_BUCKET=agrosense-datalake-prod  
networks:  
- agrosense_public_subnet  
- agrosense_private_subnet
