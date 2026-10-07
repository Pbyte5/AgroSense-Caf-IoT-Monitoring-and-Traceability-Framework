# Alembic Schema Migration & Rollout Strategy

Technical Specification for Database Versioning, Initial Rollout, and
Schema Evolution in PostgreSQL

# 1. Migration Architecture & Repository Layout

The database migration framework for AgroSense Café is built on
**Alembic** integrated with **SQLAlchemy 2.0**. This provides
deterministic, version-controlled DDL execution across local Docker
environments, CI/CD pipelines, and AWS RDS PostgreSQL production
instances.

|                                                                        |
|:-----------------------------------------------------------------------|
| **Key Architecture Principle:** All database schema changes must       |
| strictly pass through Alembic revisions. Direct DDL execution (such as |
| manual CREATE TABLE or ALTER TABLE commands in psql) is prohibited in  |
| non-local environments to prevent schema drift.                        |


### Repository Directory Structure (/alembic)

> agrosense-backend/  
> ├── alembic.ini \# Main configuration file (DB URLs, logging)  
> ├── alembic/  
> │ ├── env.py \# Migration execution context & SQLAlchemy metadata  
> │ ├── script.py.mako \# Template for generating new revision files  
> │ └── versions/ \# Ordered revision scripts  
> │ ├── 001_initial_schema.py \# Initial baseline DDL (5-Tier
> Topology)  
> │ └── 002_add_indexes.py \# Performance & audit index enhancements  
> └── app/  
> └── db/  
> └── base.py \# Declarative base importing all ORM models

# 2. Initial Revision Structure (001_initial_schema.py)

To ensure absolute referential integrity without disabling foreign key
constraints during rollout, the initial revision
**001_initial_schema.py** executes DDL creation statements according to
a strict **5-Tier Topological Sequence**. Each tier depends exclusively
on tables created in prior tiers.

| \# Tier\*\* | **Domain Category**         | \*\*Included Tables                                                                                                                                  |
|:------------|:----------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------|
| **Tier 1**  | Catalogs & Independents     | departments, users, producers, international_buyers, coffee_varieties, sensor_types, crop_nutrient_references                                        |
| **Tier 2**  | Spatial & Geographic        | municipalities, forest_reserves (with PostGIS extension enablement)                                                                                  |
| **Tier 3**  | Core Agricultural Entities  | farms, farm_plots, farm_reserve_overlaps                                                                                                             |
| **Tier 4**  | Operations & Field Hardware | iot_sensors, sensor_anomalies_log, soil_lab_analyses, fertilizer_recommendations, harvest_deliveries                                                 |
| **Tier 5**  | Aggregations & Auditing     | export_batches, batch_farm_compositions, cupping_evaluations, buyer_batch_contracts, agronomic_alerts, agronomist_field_visits, buyer_api_audit_logs |

# 3. Execution, Automation & Rollout Workflow

In the local development environment and ECS Fargate deployment,
migrations are executed automatically during container startup using the
FastAPI **entrypoint.sh** script. The rollout process ensures database
readiness before serving API traffic.

|                                                                               |
|:------------------------------------------------------------------------------|
| **Automated Rollout Sequence (entrypoint.sh):**                               |
| 1\. Wait for PostgreSQL readiness on port 5432 using 'nc -z postgres 5432'.\\ |
| 2\. Run 'alembic upgrade head' to inspect the 'alembic_version'               |
| table and apply unapplied revisions inside an atomic transaction.\\           |
| 3\. Execute synthetic seed loading scripts if SEED_ENABLED=true.\\            |
| 4\. Start the ASGI Uvicorn server on port 8000.                               |


## Developer Migration Commands

| \# Alembic Command\*\*                       | \*\*Description / Purpose                                                                          |
|:---------------------------------------------|:---------------------------------------------------------------------------------------------------|
| **alembic revision --autogenerate -m 'msg'** | Generates a new migration script by detecting differences between SQLAlchemy models and DB schema. |
| **alembic upgrade head**                     | Applies all pending migrations up to the latest revision.                                          |
| **alembic downgrade -1**                     | Rolls back the single most recent applied migration revision.                                      |
| **alembic current**                          | Displays the current revision ID stored in the alembic_version table.                              |

# 4. Guidance for Future Schema Evolution

As AgroSense Café evolves during production operations, schema changes
must adhere to zero-downtime safety guidelines to avoid table locks or
API service disruptions:

> **• Expand / Contract Pattern:** When renaming or removing columns,
> first add the new column (Expand), update application code to write to
> both columns, migrate legacy data, and finally drop the old column
> (Contract) in a subsequent release.
>
> **• Nullable Columns with Default Values:** Always define new columns
> as NULLABLE or provide a SERVER_DEFAULT value during creation to avoid
> full-table rewrite locks on large transactional tables.
>
> **• Non-blocking Index Creation:** For high-volume tables (such as
> iot_sensors or harvest_deliveries), create indexes using PostgreSQL's
> CONCURRENTLY option to prevent write locks.
>
> **• PostGIS Extension Management:** Ensure 'CREATE EXTENSION IF NOT
> EXISTS postgis;' is declared in the initial migration script before
> creating geometry columns in farms or municipalities.
