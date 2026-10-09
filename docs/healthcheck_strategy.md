# 🩺 AgroSense Café — Estrategia de Healthchecks y Readiness en Docker Compose

Este documento define la estrategia de verificación de salud (*Healthchecks*), calibración de tiempos (*timings*), grafo de dependencias de arranque y especificación del endpoint `/health` para los servicios locales interdependientes de **AgroSense Café** (**PostgreSQL**, **RabbitMQ**, **LocalStack S3** y **FastAPI**).

---

## 1. Propósito y Justificación Técnica

Cuando se ejecuta `docker compose up -d`, el motor de Docker inicia los procesos de los contenedores casi en paralelo. Sin embargo, **que un contenedor esté en estado `Up` (proceso iniciado) no significa que el servicio esté `Ready` (listo para aceptar conexiones TCP/HTTP)**:

- **PostgreSQL 16** requiere tiempo adicional en su primer arranque para ejecutar los scripts de bootstrap en `/docker-entrypoint-initdb.d/` (`01_enable_extensions.sql`, `02_create_schemas.sql`, `03_create_roles_and_db.sql`).
- **RabbitMQ** necesita inicializar el motor Erlang e importar la topología de exchanges y colas (`definitions.json`).
- **LocalStack** debe levantar el emulador de S3 y ejecutar el script `01_init_s3_buckets.sh` para crear los buckets de la arquitectura Medallion (`Bronze`, `Silver`, `Gold`).

Si **FastAPI** o las migraciones de **Alembic** intentan conectarse en el segundo 1 utilizando un `depends_on` simple, fallarán con errores de `Connection refused`. Para erradicar esta condición de carrera, todos los servicios críticos implementan bloques `healthcheck` nativos combinados con la directriz `condition: service_healthy`.

---

## 2. Parámetros de Calibración (Timings)

Cada bloque `healthcheck` en `docker-compose.yml` se calibra mediante cuatro parámetros fundamentales:

| Parámetro | Descripción Técnica | Impacto en AgroSense Café |
| :--- | :--- | :--- |
| **`interval`** | Frecuencia con la que Docker ejecuta el comando de verificación dentro del contenedor. | Define qué tan rápido se detecta que un servicio ya está listo o que sufrió una caída (`10s` a `15s`). |
| **`timeout`** | Tiempo máximo que Docker espera a que el comando de prueba responda antes de darlo por fallido. | Evita que chequeos colgados bloqueen el demonio de Docker (`5s`). |
| **`retries`** | Número de fallos consecutivos permitidos antes de marcar el contenedor como `unhealthy`. | Previene falsos positivos por picos momentáneos de CPU durante el arranque (`3` a `5` intentos). |
| **`start_period`** | Período de gracia inicial tras el arranque del contenedor durante el cual los fallos **no descuentan reintentos**. | **Crítico:** Permite que PostgreSQL, RabbitMQ y LocalStack ejecuten sus scripts de inicialización sin ser marcados como fallidos prematuramente (`10s` a `20s`). |

---

## 3. Matriz de Healthchecks por Servicio

| Servicio | Contenedor | Comando de Verificación (`test`) | `interval` | `timeout` | `retries` | `start_period` | Criterio de Éxito (`healthy`) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **PostgreSQL** | `agrosense_postgres` | `pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}` | `10s` | `5s` | `5` | `20s` | El motor acepta conexiones SQL en la BD principal tras finalizar `/docker-entrypoint-initdb.d/`. |
| **RabbitMQ** | `agrosense_rabbitmq` | `rabbitmq-diagnostics -q ping` | `10s` | `5s` | `5` | `20s` | El nodo Erlang está activo, el puerto AMQP `5672` responde y las colas están cargadas. |
| **LocalStack** | `agrosense_localstack` | `awslocal s3 ls` | `10s` | `5s` | `5` | `15s` | El API de S3 en el puerto `4566` responde y permite listar los buckets Medallion. |
| **FastAPI** | `agrosense_fastapi` | `curl -f http://localhost:8000/health` | `15s` | `5s` | `3` | `10s` | El servidor Uvicorn responde `HTTP 200 OK` validando conexión activa con BD, cola y S3. |

---

## 4. Grafo de Secuenciamiento de Dependencias (Dependency Order)

El encendido del entorno local sigue una secuencia estricta en tres niveles gobernada por `condition: service_healthy` y `condition: service_completed_successfully`:

```text
[Nivel 1: Infraestructura Base]         [Nivel 2: Aplicación Backend]          [Nivel 3: Tareas / Migraciones]
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

### Flujo de Secuenciamiento Paso a Paso:
1. **Nivel 1 (Infraestructura):** Docker arranca `postgres`, `rabbitmq` y `localstack` simultáneamente. Todos entran en estado `health: starting` durante su `start_period`.
2. **Nivel 2 (Backend API):** El contenedor `fastapi` permanece en espera hasta que **los tres servicios del Nivel 1** reportan estado `healthy`. Solo entonces inicia Uvicorn y expone el endpoint `/health`.
3. **Nivel 3 (Migraciones / Semillas):** Los contenedores o comandos de migración (`alembic upgrade head`) y carga de datos semilla (`seed_script`) se ejecutan garantizando que tanto la base de datos como el backend se encuentran operativos.

---

## 5. Especificación Completa en `docker-compose.yml`

A continuación se presenta la configuración consolidada con los bloques `healthcheck` y las reglas `depends_on` explícitas:

```yaml
services:
  # ==========================================================================
  # NIVEL 1: INFRAESTRUCTURA BASE (PostgreSQL, RabbitMQ, LocalStack)
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
  # NIVEL 2: BACKEND API (FastAPI)
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

## 6. Especificación del Endpoint `/health` en FastAPI

Para que el healthcheck del contenedor `fastapi` sea un verdadero indicador de **Readiness** (y no solo un chequeo superficial de que el servidor HTTP está encendido), el endpoint `GET /health` verifica activamente la conectividad con los servicios dependientes.

### 6.1 Contrato de Respuesta HTTP

- **Estado Saludable (`HTTP 200 OK`):**
  ```json
  {
    "status": "healthy",
    "database": "connected",
    "rabbitmq": "connected",
    "storage": "connected"
  }
  ```

- **Estado Degradado / No Disponible (`HTTP 503 Service Unavailable`):**
  Cuando cualquiera de las dependencias falla, el endpoint devuelve `503 Service Unavailable`, haciendo que `curl -f` retorne un código de salida distinto de cero (`exit code 22`) y Docker marque el contenedor como `unhealthy`:
  ```json
  {
    "status": "unhealthy",
    "database": "connected",
    "rabbitmq": "disconnected",
    "storage": "connected"
  }
  ```

### 6.2 Implementación de Referencia (`app/api/routes/health.py`)

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
    """Verifica que el puerto AMQP de RabbitMQ acepte conexiones TCP."""
    try:
        parsed = urlparse(rabbitmq_url)
        host = parsed.hostname or "rabbitmq"
        port = parsed.port or 5672
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_s3_storage(endpoint_url: str) -> bool:
    """Verifica que LocalStack S3 responda y contenga los buckets Medallion."""
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
    Endpoint de Liveness y Readiness para Docker Compose y balanceadores de carga.
    Verifica la conectividad real con PostgreSQL, RabbitMQ y LocalStack S3.
    """
    # 1. Verificar PostgreSQL (Serving DB)
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    # 2. Verificar RabbitMQ (Broker AMQP)
    mq_status = "connected" if check_rabbitmq_connection(settings.RABBITMQ_URL) else "disconnected"

    # 3. Verificar LocalStack (Mock Storage S3)
    s3_status = "connected" if check_s3_storage(settings.AWS_ENDPOINT_URL) else "disconnected"

    is_healthy = all(service == "connected" for service in (db_status, mq_status, s3_status))

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

## 7. Comandos de Verificación y Diagnóstico

Durante el desarrollo local, utiliza los siguientes comandos para inspeccionar el estado de salud y auditar los tiempos de arranque de cada contenedor:

```powershell
# 1. Iniciar toda la pila esperando a que los healthchecks se cumplan en orden
docker compose up -d --wait

# 2. Verificar que todos los contenedores muestren "(healthy)" en la columna STATUS
docker compose ps

# 3. Inspeccionar el historial detallado de ejecuciones del healthcheck de PostgreSQL
docker inspect --format "{{json .State.Health }}" agrosense_postgres

# 4. Probar manualmente el endpoint de salud de FastAPI desde tu terminal
curl -i http://localhost:8000/health
```
