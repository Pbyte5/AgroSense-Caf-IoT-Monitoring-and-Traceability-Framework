# PostgreSQL Initialization and Bootstrap in Docker

This document defines the directory structure, the volume configuration in Docker Compose, and the SQL bootstrap scripts that run automatically when the local **PostgreSQL 16** container is initialized for the **AgroSense Café** project.

---

## 1. Purpose and Scope

While the **SQLAlchemy 2.0** models and **Alembic** manage the creation and migration of the application's tables, the **Docker Bootstrap** process prepares the base infrastructure of the PostgreSQL engine before the application connects for the first time:

- Enabling native extensions at the superuser level (`pgcrypto`, `uuid-ossp`).
- Creating isolated logical schemas (`agrosense`).
- Configuring least-privilege database roles and creating the parallel database for automated tests (`pytest`).

---

## 2. Repository Folder Structure (`/docker`)

All local database infrastructure artifacts are stored under the `/docker/postgres/init/` directory at the repository root:

```text
agrosense-cafe/
├── app/
├── docker/
│   └── postgres/
│       └── init/                        # Automatic bootstrap SQL scripts
│           ├── 01_enable_extensions.sql # Extensions (pgcrypto, uuid-ossp)
│           ├── 02_create_schemas.sql    # Logical schemas and search_path
│           └── 03_create_roles_and_db.sql # Roles, permissions, and test DB
├── .env.example
└── docker-compose.yml
```

---

## 3. Volume Configuration and Mapping in `docker-compose.yml`

The official `postgres:16-alpine` image automatically runs any `.sql` or `.sh` file located inside the container's internal `/docker-entrypoint-initdb.d/` directory.

```yaml
services:
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
      # 1. Read-only (:ro) mount of the initialization scripts
      - ./docker/postgres/init:/docker-entrypoint-initdb.d:ro
      # 2. Named volume for local data persistence
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-agrosense_user} -d ${POSTGRES_DB:-agrosense_db}"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
    name: agrosense_postgres_data
```

> 💡 **Security Note (`:ro`):** The `./docker/postgres/init` directory is mounted with the `:ro` (*read-only*) flag to guarantee that the container cannot modify or delete the scripts versioned in Git.

---

## 4. Execution Order and SQL Script Specification

The official PostgreSQL entrypoint runs the files inside `/docker-entrypoint-initdb.d/` in **strict alphabetical order**. For this reason, a sequential numeric prefix is used (`01_`, `02_`, `03_`):

|     Order     | File                           | Main Responsibility                                                                                                                         |
| :-----------: | :----------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------ |
| **1st** | `01_enable_extensions.sql`   | Installs `pgcrypto` and `uuid-ossp` to support `gen_random_uuid()` in `UUID` primary keys.                                              |
| **2nd** | `02_create_schemas.sql`      | Creates the `agrosense` logical schema and sets the database's default `search_path`.                                                     |
| **3rd** | `03_create_roles_and_db.sql` | Configures application/read-only roles, grants privileges on the schema, and creates the test database (`agrosense_test_db`).              |

---

### 4.1 Script 1: `docker/postgres/init/01_enable_extensions.sql`

Enables the required cryptographic extensions before Alembic runs the table migrations:

```sql
-- ============================================================================
-- 01_enable_extensions.sql
-- Enables extensions required by the AgroSense Café relational model
-- ============================================================================

\connect agrosense_db;

-- Required for native UUIDv4 generation via gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Complementary extension for standard UUID functions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

---

### 4.2 Script 2: `docker/postgres/init/02_create_schemas.sql`

Isolates the business domain tables and standardizes the time zone to UTC:

```sql
-- ============================================================================
-- 02_create_schemas.sql
-- Creates project schemas and sets default parameters in UTC
-- ============================================================================

\connect agrosense_db;

-- Create the application's main schema
CREATE SCHEMA IF NOT EXISTS agrosense AUTHORIZATION agrosense_user;

-- Set the search_path so SQLAlchemy/Alembic resolve the schema automatically
ALTER DATABASE agrosense_db SET search_path TO agrosense, public;

-- Force storage and operations of timestamps (TIMESTAMPTZ) in UTC
ALTER DATABASE agrosense_db SET timezone TO 'UTC';
```

---

### 4.3 Script 3: `docker/postgres/init/03_create_roles_and_db.sql`

Configures differentiated roles (read/write for the FastAPI backend and read-only for analytical queries/Power BI) and provisions the isolated database for `pytest`:

```sql
-- ============================================================================
-- 03_create_roles_and_db.sql
-- Configures access roles and a secondary database for tests (Pytest)
-- ============================================================================

-- 1. Create a read-only role for local analytics and auditing (Power BI / BI)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'agrosense_readonly') THEN
        CREATE ROLE agrosense_readonly WITH LOGIN PASSWORD 'readonly_local_pass';
    END IF;
END
$$;

-- Grant read permissions on the main schema
GRANT CONNECT ON DATABASE agrosense_db TO agrosense_readonly;
GRANT USAGE ON SCHEMA agrosense, public TO agrosense_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA agrosense, public TO agrosense_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA agrosense GRANT SELECT ON TABLES TO agrosense_readonly;

-- 2. Create an isolated database for the test suite (uv run pytest)
SELECT 'CREATE DATABASE agrosense_test_db OWNER agrosense_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'agrosense_test_db')\gexec

\connect agrosense_test_db;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE SCHEMA IF NOT EXISTS agrosense AUTHORIZATION agrosense_user;
ALTER DATABASE agrosense_test_db SET search_path TO agrosense, public;
ALTER DATABASE agrosense_test_db SET timezone TO 'UTC';
```

---

## 5. Container Lifecycle and Full Reset

### 5.1 Single-Execution Rule

The PostgreSQL engine runs the scripts in `/docker-entrypoint-initdb.d/` **only when the data directory (`/var/lib/postgresql/data`) is empty**, that is, the first time the `postgres_data` volume is created.

- If you stop the container (`docker compose stop` or `docker compose down`) and start it again (`docker compose up -d`), the previous data is preserved and **the bootstrap scripts are skipped**.
- If you modify any of the `01_`, `02_`, or `03_` files, the changes will not be applied automatically to an already existing volume.

### 5.2 Operation and Forced Reset Commands

```powershell
# 1. Start the database in the background for the first time
docker compose up -d postgres

# 2. Check in the logs that scripts 01, 02, and 03 ran without errors
docker compose logs -f postgres

# 3. Verify the created extensions and schemas from the terminal
docker exec -it agrosense_postgres psql -U agrosense_user -d agrosense_db -c "\dx"
docker exec -it agrosense_postgres psql -U agrosense_user -d agrosense_db -c "\dn"
```

To **force a full re-initialization** from scratch (for example, after updating a bootstrap script or corrupting local test data), destroy the container together with its associated volume (`-v`) and bring it up again:

```powershell
# Destroy containers and remove the postgres_data volume (-v)
docker compose down -v

# Recreate the volume and run all scripts in /docker/postgres/init/
docker compose up -d postgres
```
