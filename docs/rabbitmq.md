# 🐇📦 AgroSense Café — Especificación de Configuración para RabbitMQ y Mock Storage (LocalStack S3)

Este documento establece los requerimientos técnicos de configuración, persistencia de datos, credenciales por defecto, topología inicial de colas, buckets S3 y endpoints de red para los contenedores de **RabbitMQ** y **LocalStack (Mock Storage)** en el entorno de desarrollo local de **AgroSense Café**.

---

## 1. Propósito en la Arquitectura Local

Para emular el flujo *end-to-end* sin incurrir en costos operativos en la nube (RNF-04) ni depender de conectividad constante a AWS durante el desarrollo, el entorno Docker incorpora dos servicios clave junto a PostgreSQL:

1. **RabbitMQ (Capa de Ingesta Desacoplada):** Actúa como el broker de mensajería con confirmación (`ACK`) para recibir las cargas en bloque (*block uploads*) de hasta 7 días provenientes de los sensores IoT (RNF-01) y encolar las extracciones climáticas programadas sin saturar el backend FastAPI.
2. **LocalStack (Emulador Local de Amazon S3):** Simula localmente el Data Lake para almacenar los objetos crudos y procesados (JSON/Parquet con particionamiento diario) a través de las tres capas de la arquitectura **Medallion** (`Bronze`, `Silver` y `Gold`).

---

## 2. Estructura de Directorios en el Repositorio (`/docker`)

Siguiendo el estándar del proyecto, los archivos de configuración y bootstrap automático de RabbitMQ y LocalStack se alojan dentro de la carpeta `/docker`:

```text
agrosense-cafe/
├── app/
├── docker/
│   ├── postgres/
│   │   └── init/
│   │       ├── 01_enable_extensions.sql
│   │       ├── 02_create_schemas.sql
│   │       └── 03_create_roles_and_db.sql
│   ├── rabbitmq/
│   │   ├── rabbitmq.conf              # Configuración de arranque del broker
│   │   └── definitions.json           # Topología predefinida (Exchanges, Queues y DLQ)
│   └── localstack/
│       └── init/
│           └── 01_init_s3_buckets.sh  # Script bootstrap para buckets Medallion
├── .env.example
└── docker-compose.yml
```

---

## 3. Especificación del Contenedor RabbitMQ

### 3.1 Parámetros Técnicos y de Ejecución
- **Imagen Oficial:** `rabbitmq:3.13-management-alpine` (incluye el plugin web de administración y métricas Prometheus).
- **Puertos Expuestos:**
  - `5672`: Puerto del protocolo **AMQP 0-9-1** para publicación y consumo desde FastAPI y workers.
  - `15672`: Interfaz web **RabbitMQ Management UI** (`http://localhost:15672`).
- **Persistencia de Datos:** Volumen nombrado `rabbitmq_data` montado en `/var/lib/rabbitmq` para conservar mensajes en disco (`durable: true`) ante reinicios del contenedor.
- **Garantía de Entrega (RNF-01):** Todas las colas se declaran como **durables** (`durable: true`) y exigen confirmación explícita del consumidor (`manual ACK`) antes de eliminar un bloque de lecturas de la cola.

### 3.2 Topología Inicial de Colas (`docker/rabbitmq/definitions.json`)
Al iniciar el contenedor, RabbitMQ importa automáticamente las siguientes colas y exchanges en el virtual host `/agrosense`:

| Recurso | Tipo | Nombre | Propósito en AgroSense Café |
| :--- | :--- | :--- | :--- |
| **Exchange Principal** | `topic` | `agrosense.ingest.exchange` | Enruta mensajes según el tipo de fuente (`telemetry.*`, `climate.*`). |
| **Exchange DLX** | `direct` | `agrosense.dlx.exchange` | Captura bloques corruptos o rechazados tras agotar reintentos. |
| **Cola IoT (F4)** | `classic (durable)` | `telemetry.raw.queue` | Recibe bloques de lecturas de sensores IoT (hasta 7 días acumulados) con confirmación `ACK`. |
| **Cola Clima (F2/F3)** | `classic (durable)` | `climate.ingest.queue` | Encola las descargas diarias de NASA POWER y Open-Meteo. |
| **Dead Letter Queue** | `classic (durable)` | `dead.letter.queue` | Almacena cargas fallidas para auditoría e inserción en `sensor_anomalies_log`. |

#### Archivo `docker/rabbitmq/rabbitmq.conf`:
```ini
loopback_users.guest = false
listeners.tcp.default = 5672
management.tcp.port = 15672
management.load_definitions = /etc/rabbitmq/definitions.json
## Límite de memoria seguro para desarrollo local
vm_memory_high_watermark.relative = 0.6
```

#### Archivo `docker/rabbitmq/definitions.json`:
```json
{
  "vhosts": [
    { "name": "/" },
    { "name": "/agrosense" }
  ],
  "permissions": [
    {
      "user": "agrosense_mq",
      "vhost": "/agrosense",
      "configure": ".*",
      "write": ".*",
      "read": ".*"
    }
  ],
  "exchanges": [
    {
      "name": "agrosense.ingest.exchange",
      "vhost": "/agrosense",
      "type": "topic",
      "durable": true,
      "auto_delete": false
    },
    {
      "name": "agrosense.dlx.exchange",
      "vhost": "/agrosense",
      "type": "direct",
      "durable": true,
      "auto_delete": false
    }
  ],
  "queues": [
    {
      "name": "telemetry.raw.queue",
      "vhost": "/agrosense",
      "durable": true,
      "auto_delete": false,
      "arguments": {
        "x-dead-letter-exchange": "agrosense.dlx.exchange",
        "x-dead-letter-routing-key": "dlq.telemetry",
        "x-message-ttl": 604800000
      }
    },
    {
      "name": "climate.ingest.queue",
      "vhost": "/agrosense",
      "durable": true,
      "auto_delete": false,
      "arguments": {
        "x-dead-letter-exchange": "agrosense.dlx.exchange",
        "x-dead-letter-routing-key": "dlq.climate"
      }
    },
    {
      "name": "dead.letter.queue",
      "vhost": "/agrosense",
      "durable": true,
      "auto_delete": false
    }
  ],
  "bindings": [
    {
      "source": "agrosense.ingest.exchange",
      "vhost": "/agrosense",
      "destination": "telemetry.raw.queue",
      "destination_type": "queue",
      "routing_key": "telemetry.block.#"
    },
    {
      "source": "agrosense.ingest.exchange",
      "vhost": "/agrosense",
      "destination": "climate.ingest.queue",
      "destination_type": "queue",
      "routing_key": "climate.daily.#"
    },
    {
      "source": "agrosense.dlx.exchange",
      "vhost": "/agrosense",
      "destination": "dead.letter.queue",
      "destination_type": "queue",
      "routing_key": "dlq.telemetry"
    },
    {
      "source": "agrosense.dlx.exchange",
      "vhost": "/agrosense",
      "destination": "dead.letter.queue",
      "destination_type": "queue",
      "routing_key": "dlq.climate"
    }
  ]
}
```

---

## 4. Especificación del Contenedor Mock Storage (LocalStack S3)

### 4.1 Parámetros Técnicos y de Ejecución
- **Imagen Oficial:** `localstack/localstack:3.7`
- **Servicios Emulados (`SERVICES`):** `s3` (restringido únicamente a S3 para optimizar consumo de RAM y arranque rápido).
- **Puerto Unificado (Edge Port):** `4566` (`http://localhost:4566`).
- **Persistencia de Datos:**
  - Variable `PERSISTENCE=1` habilitada.
  - Volumen nombrado `localstack_data` montado en `/var/lib/localstack`.
- **Credenciales Mock por Defecto:**
  - `AWS_ACCESS_KEY_ID=test`
  - `AWS_SECRET_ACCESS_KEY=test`
  - `AWS_DEFAULT_REGION=us-east-1`

### 4.2 Script de Inicialización de Buckets Medallion (`docker/localstack/init/01_init_s3_buckets.sh`)
LocalStack ejecuta automáticamente todos los scripts ubicados en `/etc/localstack/init/ready.d/` una vez que el servicio está listo. Este script crea los tres buckets del Data Lake local y su estructura base para particionamiento diario (`dt=YYYY-MM-DD`):

```bash
#!/usr/bin/env bash
# ============================================================================
# 01_init_s3_buckets.sh
# Crea automáticamente los buckets S3 locales para la arquitectura Medallion
# ============================================================================

set -euo pipefail

echo "🚀 Inicializando buckets S3 de AgroSense Café en LocalStack..."

BUCKETS=(
  "agrosense-bronze-local"
  "agrosense-silver-local"
  "agrosense-gold-local"
)

for BUCKET in "${BUCKETS[@]}"; do
  awslocal s3 mb "s3://${BUCKET}" --region us-east-1 || true
  echo "✅ Bucket verificado/creado: s3://${BUCKET}"
done

# Crear prefijos base para particionamiento diario (Bronze / Silver / Gold)
awslocal s3api put-object --bucket agrosense-bronze-local --key iot_telemetry/
awslocal s3api put-object --bucket agrosense-bronze-local --key weather_nasa_power/
awslocal s3api put-object --bucket agrosense-bronze-local --key weather_open_meteo/

awslocal s3api put-object --bucket agrosense-silver-local --key telemetry_cleaned/
awslocal s3api put-object --bucket agrosense-silver-local --key weather_validated/

awslocal s3api put-object --bucket agrosense-gold-local --key agronomic_alerts/
awslocal s3api put-object --bucket agrosense-gold-local --key sustainability_indicators/

echo "🎉 Inicialización de Mock Storage (S3 Medallion) completada."
```

> ⚠️ **Importante:** Asegúrate de otorgar permisos de ejecución al script antes de hacer commit en Git: `git update-index --chmod=+x docker/localstack/init/01_init_s3_buckets.sh`.

---

## 5. Definición Completa en `docker-compose.yml` y Red Interna

Todos los contenedores se comunican dentro de la red puente dedicada `agrosense_network`:

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
      - ./docker/postgres/init:/docker-entrypoint-initdb.d:ro
      - postgres_data:/var/lib/postgresql/data
    networks:
      - agrosense_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-agrosense_user} -d ${POSTGRES_DB:-agrosense_db}"]
      interval: 5s
      timeout: 5s
      retries: 5

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

## 6. Matriz de Endpoints y Variables de Entorno (`.env.example`)

### 6.1 Tabla de Endpoints de Servicio

| Servicio | Protocolo / Interfaz | Endpoint desde el Host (Tu PC) | Endpoint Interno (Red Docker `agrosense_network`) |
| :--- | :--- | :--- | :--- |
| **PostgreSQL** | TCP (`psql` / SQLAlchemy) | `localhost:5432` | `postgres:5432` |
| **RabbitMQ Broker** | AMQP 0-9-1 | `amqp://localhost:5672/%2Fagrosense` | `amqp://rabbitmq:5672/%2Fagrosense` |
| **RabbitMQ UI** | HTTP (Web Dashboard) | `http://localhost:15672` | `http://rabbitmq:15672` |
| **LocalStack (S3)** | HTTP (AWS S3 API) | `http://localhost:4566` | `http://localstack:4566` |

### 6.2 Configuración de Variables en `.env.example`

```dotenv
# ============================================================================
# PostgreSQL (Serving Database)
# ============================================================================
POSTGRES_DB=agrosense_db
POSTGRES_USER=agrosense_user
POSTGRES_PASSWORD=agrosense_password
POSTGRES_PORT=5432
DATABASE_URL=postgresql+psycopg://agrosense_user:agrosense_password@localhost:5432/agrosense_db

# ============================================================================
# RabbitMQ (Ingesta IoT con ACK y Cola de Clima)
# ============================================================================
RABBITMQ_DEFAULT_USER=agrosense_mq
RABBITMQ_DEFAULT_PASS=agrosense_mq_secret
RABBITMQ_DEFAULT_VHOST=/agrosense
RABBITMQ_AMQP_PORT=5672
RABBITMQ_MGMT_PORT=15672
# URL para uso local fuera de Docker:
RABBITMQ_URL=amqp://agrosense_mq:agrosense_mq_secret@localhost:5672/%2Fagrosense
# URL para uso interno entre contenedores Docker:
# RABBITMQ_URL=amqp://agrosense_mq:agrosense_mq_secret@rabbitmq:5672/%2Fagrosense

# ============================================================================
# Mock Storage — LocalStack S3 (Data Lake Medallion)
# ============================================================================
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1
LOCALSTACK_PORT=4566
AWS_ENDPOINT_URL=http://localhost:4566
# AWS_ENDPOINT_URL=http://localstack:4566  # (Usar dentro de contenedores Docker)

S3_BUCKET_BRONZE=agrosense-bronze-local
S3_BUCKET_SILVER=agrosense-silver-local
S3_BUCKET_GOLD=agrosense-gold-local
```

---

## 7. Comandos de Verificación y Diagnóstico Local

Una vez levantado el entorno con `docker compose up -d`, ejecuta los siguientes comandos para verificar que las colas y los buckets S3 se crearon correctamente:

```powershell
# 1. Verificar el estado de salud (Healthy) de los 3 contenedores
docker compose ps

# 2. Listar las colas creadas en RabbitMQ dentro del vhost /agrosense
docker exec -it agrosense_rabbitmq rabbitmqctl list_queues -p /agrosense name durable messages

# 3. Verificar que los 3 buckets Medallion existen en LocalStack S3
docker exec -it agrosense_localstack awslocal s3 ls

# 4. Consultar los prefijos creados dentro del bucket Bronze
docker exec -it agrosense_localstack awslocal s3 ls s3://agrosense-bronze-local/
```