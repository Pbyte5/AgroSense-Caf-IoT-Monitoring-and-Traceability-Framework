# 🐳 AgroSense Café — Inicialización y Bootstrap de PostgreSQL en Docker

Este documento define la estructura de directorios, la configuración de volúmenes en Docker Compose y los scripts SQL de arranque (*bootstrap*) que se ejecutan automáticamente al inicializar el contenedor local de **PostgreSQL 16** para el proyecto **AgroSense Café**.

---

## 1. Propósito y Alcance

Mientras que los modelos de **SQLAlchemy 2.0** y **Alembic** gestionan la creación y migración de tablas de la aplicación, el proceso de **Bootstrap en Docker** prepara la infraestructura base del motor PostgreSQL antes de que la aplicación se conecte por primera vez:

- Habilitación de extensiones nativas a nivel de superusuario (`pgcrypto`, `uuid-ossp`).
- Creación de esquemas lógicos aislados (`agrosense`).
- Configuración de roles de base de datos con mínimo privilegio y creación de la base de datos paralela para pruebas automatizadas (`pytest`).

---

## 2. Estructura de Carpetas en el Repositorio (`/docker`)

Todos los artefactos de infraestructura local de base de datos se almacenan bajo el directorio `/docker/postgres/init/` en la raíz del repositorio:

```text
agrosense-cafe/
├── app/
├── docker/
│   └── postgres/
│       └── init/                        # Scripts SQL de bootstrap automático
│           ├── 01_enable_extensions.sql # Extensiones (pgcrypto, uuid-ossp)
│           ├── 02_create_schemas.sql    # Esquemas lógicos y search_path
│           └── 03_create_roles_and_db.sql # Roles, permisos y BD de pruebas
├── .env.example
└── docker-compose.yml
```

---

## 3. Configuración y Mapeo de Volúmenes en `docker-compose.yml`

La imagen oficial `postgres:16-alpine` ejecuta automáticamente cualquier archivo `.sql` o `.sh` ubicado dentro del directorio interno `/docker-entrypoint-initdb.d/` del contenedor.

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
      # 1. Montaje en modo solo lectura (:ro) de los scripts de inicialización
      - ./docker/postgres/init:/docker-entrypoint-initdb.d:ro
      # 2. Volumen nombrado para persistencia de datos locales
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

> 💡 **Nota de Seguridad (`:ro`):** El directorio `./docker/postgres/init` se monta con el flag `:ro` (*read-only*) para garantizar que el contenedor no pueda modificar ni eliminar los scripts versionados en Git.

---

## 4. Orden de Ejecución y Especificación de Scripts SQL

El entrypoint oficial de PostgreSQL ejecuta los archivos dentro de `/docker-entrypoint-initdb.d/` en **estricto orden alfabético**. Por ello, se utiliza un prefijo numérico secuencial (`01_`, `02_`, `03_`):

| Orden | Archivo | Responsabilidad Principal |
| :---: | :--- | :--- |
| **1°** | `01_enable_extensions.sql` | Instala `pgcrypto` y `uuid-ossp` para soportar `gen_random_uuid()` en llaves primarias `UUID`. |
| **2°** | `02_create_schemas.sql` | Crea el esquema lógico `agrosense` y configura el `search_path` por defecto de la base de datos. |
| **3°** | `03_create_roles_and_db.sql` | Configura roles de aplicación/lectura, asigna privilegios sobre el esquema y crea la base de datos de pruebas (`agrosense_test_db`). |

---

### 4.1 Script 1: `docker/postgres/init/01_enable_extensions.sql`

Habilita las extensiones criptográficas necesarias antes de que Alembic ejecute las migraciones de las tablas:

```sql
-- ============================================================================
-- 01_enable_extensions.sql
-- Habilita extensiones requeridas por el modelo relacional de AgroSense Café
-- ============================================================================

\connect agrosense_db;

-- Requerido para generación nativa de UUIDv4 mediante gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Extensión complementaria para funciones UUID estándar
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

---

### 4.2 Script 2: `docker/postgres/init/02_create_schemas.sql`

Aísla las tablas del dominio de negocio y estandariza la zona horaria en UTC:

```sql
-- ============================================================================
-- 02_create_schemas.sql
-- Crea esquemas del proyecto y configura parámetros por defecto en UTC
-- ============================================================================

\connect agrosense_db;

-- Crear esquema principal de la aplicación
CREATE SCHEMA IF NOT EXISTS agrosense AUTHORIZATION agrosense_user;

-- Configurar el search_path para que SQLAlchemy/Alembic resuelvan el esquema automáticamente
ALTER DATABASE agrosense_db SET search_path TO agrosense, public;

-- Forzar almacenamiento y operaciones de marcas de tiempo (TIMESTAMPTZ) en UTC
ALTER DATABASE agrosense_db SET timezone TO 'UTC';
```

---

### 4.3 Script 3: `docker/postgres/init/03_create_roles_and_db.sql`

Configura roles diferenciados (lectura/escritura para el backend FastAPI y solo lectura para consultas analíticas/Power BI) y aprovisiona la base de datos aislada para `pytest`:

```sql
-- ============================================================================
-- 03_create_roles_and_db.sql
-- Configura roles de acceso y base de datos secundaria para pruebas (Pytest)
-- ============================================================================

-- 1. Crear rol de solo lectura para analítica local y auditoría (Power BI / BI)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'agrosense_readonly') THEN
        CREATE ROLE agrosense_readonly WITH LOGIN PASSWORD 'readonly_local_pass';
    END IF;
END
$$;

-- Otorgar permisos de lectura sobre el esquema principal
GRANT CONNECT ON DATABASE agrosense_db TO agrosense_readonly;
GRANT USAGE ON SCHEMA agrosense, public TO agrosense_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA agrosense, public TO agrosense_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA agrosense GRANT SELECT ON TABLES TO agrosense_readonly;

-- 2. Crear base de datos aislada para la suite de pruebas (uv run pytest)
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

## 5. Ciclo de Vida del Contenedor y Reinicio Total (Container Lifecycle)

### 5.1 Regla de Ejecución Única
El motor de PostgreSQL ejecuta los scripts de `/docker-entrypoint-initdb.d/` **únicamente cuando el directorio de datos (`/var/lib/postgresql/data`) está vacío**, es decir, la primera vez que se crea el volumen `postgres_data`.

- Si detienes el contenedor (`docker compose stop` o `docker compose down`) y lo vuelves a iniciar (`docker compose up -d`), los datos previos se conservan y **los scripts de bootstrap se omiten**.
- Si modificas alguno de los archivos `01_`, `02_` o `03_`, los cambios no se aplicarán automáticamente sobre un volumen ya existente.

### 5.2 Comandos de Operación y Reinicio Forzado

```powershell
# 1. Levantar la base de datos por primera vez en segundo plano
docker compose up -d postgres

# 2. Verificar en los logs que los scripts 01, 02 y 03 se ejecutaron sin errores
docker compose logs -f postgres

# 3. Comprobar las extensiones y esquemas creados desde la terminal
docker exec -it agrosense_postgres psql -U agrosense_user -d agrosense_db -c "\dx"
docker exec -it agrosense_postgres psql -U agrosense_user -d agrosense_db -c "\dn"
```

Para **forzar una re-inicialización completa** desde cero (por ejemplo, tras actualizar un script de bootstrap o corromper datos locales de prueba), destruye el contenedor junto con su volumen asociado (`-v`) y vuelve a levantarlo:

```powershell
# Destruir contenedores y eliminar el volumen postgres_data (-v)
docker compose down -v

# Volver a crear el volumen y ejecutar todos los scripts de /docker/postgres/init/
docker compose up -d postgres
```
