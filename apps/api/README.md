# AgroSense Café API

FastAPI service package. Run from the repository root with:

```powershell
uv run --package agrosense-api fastapi dev apps/api/src/agrosense_api/script.py
```

The API exposes public `GET /health` and JWT-protected routes under `/api/v1`.
Configure the service with `AGROSENSE_` environment variables:

| Variable | Purpose |
| --- | --- |
| `AGROSENSE_DATABASE_URL` | SQLAlchemy async URL; use `postgresql+asyncpg://...` for PostGIS |
| `AGROSENSE_DATABASE_POOL_SIZE` | SQLAlchemy connection pool size (default: 10) |
| `AGROSENSE_DATABASE_MAX_OVERFLOW` | Additional connections allowed above the pool size (default: 20) |
| `AGROSENSE_DATABASE_POOL_TIMEOUT_SECONDS` | Seconds to wait for a pooled connection (default: 30) |
| `AGROSENSE_DATABASE_POOL_RECYCLE_SECONDS` | Connection recycle interval (default: 1800) |
| `AGROSENSE_JWT_SECRET_KEY` | Long random secret used to sign access tokens |
| `AGROSENSE_JWT_ACCESS_TOKEN_MINUTES` | Access-token lifetime (default: 30) |
| `AGROSENSE_BUYER_JWT_SECRET_KEY` | Separate signing secret for buyer access tokens |
| `AGROSENSE_BUYER_JWT_ISSUER` | Trusted buyer-token issuer (default: `agrosense-buyer-auth`) |
| `AGROSENSE_AUTH_USERNAME` | Single configured API operator |
| `AGROSENSE_AUTH_PASSWORD_HASH` | Passlib Argon2 hash for the operator password |
| `AGROSENSE_AUTH_SCOPES` | JSON array of OAuth scopes granted to issued tokens |
| `AGROSENSE_RABBITMQ_URL` | AMQP URL for telemetry publishing |
| `AGROSENSE_ALLOWED_ORIGINS` | JSON array of allowed browser origins |

Create an Argon2 password hash with:

```powershell
uv run --package agrosense-api python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['argon2']).hash('REPLACE_ME'))"
```

For deployment, set a generated password and secret through the secret manager;
do not commit them. The local default database URL is SQLite for basic API-only development; the
spatial Farm model and all database-backed routes require PostgreSQL with
PostGIS. Apply migrations with
`uv run --package agrosense-api alembic -c apps/api/alembic.ini upgrade head`.
Rate limits use SlowAPI's in-process storage and should be backed by shared
storage when running multiple workers.

The soil recommendations are intentionally conservative screening rules, not
fertilizer prescriptions; confirm measurements and treatments with a qualified
agronomist.

RN-07 evaluates normalized soil values in mg/kg against the F1 reference for
the plot's coffee variety and growth stage. The initial prototype uses a
soil-to-application conversion factor of `0.5` kg/ha per mg/kg deficit and a
traditional-dose baseline of `200` kg/ha. These assumptions need agronomic
calibration for the local soil depth, bulk density, and nutrient availability;
they are not validated fertilizer prescriptions.

## Connect to PostgreSQL/PostGIS

Create a PostgreSQL database with PostGIS enabled, then set the service
environment before starting it. For local PowerShell development, for example:

```powershell
$env:AGROSENSE_DATABASE_URL = "postgresql+asyncpg://USER:PASSWORD@localhost:5432/agrosense"
$env:AGROSENSE_JWT_SECRET_KEY = "REPLACE_WITH_A_RANDOM_SECRET_OF_AT_LEAST_32_CHARACTERS"
$env:AGROSENSE_AUTH_USERNAME = "operator"
$env:AGROSENSE_AUTH_PASSWORD_HASH = "REPLACE_WITH_THE_ARGON2_HASH"
uv run --package agrosense-api alembic -c apps/api/alembic.ini upgrade head
uv run --package agrosense-api fastapi dev apps/api/src/agrosense_api/script.py
```

Use a secret manager for deployed credentials rather than committing a `.env`
file. The migrations create the initial schema and the incremental soil-analysis,
fertilizer-recommendation, and agronomic-alert tables, including PostGIS geometry
columns, spatial indexes, and the composition-protection trigger. Review them
against any existing database before applying them.

Interactive API documentation is available at `/docs` (Swagger UI) and
`/redoc`; the generated contract is OpenAPI 3.0.3 at `/openapi.json`.

## API integration flow

1. Configure the operator credentials and request a token from
   `POST /api/v1/auth/token` using OAuth2 form fields `username` and `password`.
   Send the returned access token as `Authorization: Bearer <token>`.
2. Buyer certificates are grouped separately under the `Compradores` tag in
   Swagger and Redoc. `GET /api/v1/traceability/{batch_code}` requires a
   signed buyer JWT with a `buyer_id` UUID claim and the
   `traceability:read` scope. The API filters by both batch code and that
   buyer ID; a lot assigned to another buyer returns HTTP 403, while an
   unknown code returns HTTP 404.
3. The current `/api/v1/auth/token` endpoint issues operator tokens only; it
   does not create buyer identities or buyer tokens. Configure a separate,
   strong `AGROSENSE_BUYER_JWT_SECRET_KEY` and the expected issuer, then
   connect a trusted identity provider that issues buyer tokens with those
   settings and the required claims. Keep the buyer signing secret separate
   from `AGROSENSE_JWT_SECRET_KEY`; do not use a caller-supplied `X-Buyer-ID`
   header for access control because clients can forge it.
4. Load farm boundaries as PostGIS polygons, regional `water_usage_m3_ton`
   baselines, the forest-reserve boundary catalog, and positive
   `batch_farm_compositions` before certification. Composition contributions
   must sum exactly to the lot's positive net weight.
5. Internal API consumers can read `GET /api/v1/lots/{lot_id}` and
   `GET /api/v1/farms/{farm_id}`. Submit `POST /api/v1/lots/certify` with
   `{"lot_id": "<UUID>"}`
   to validate origin, reserve intersections, and an SCA score from 80 through
   100, and atomically store the certificate and traceability event. The
   latest fertilizer recommendation is used when present; otherwise its
   weighted reduction is zero.
6. Connect telemetry producers to `POST /api/v1/telemetry`; configure
   `AGROSENSE_RABBITMQ_URL` and provision the configured queue when enabling
   RabbitMQ publishing.

The database query paths include eager-loaded lot composition, paginated farm
contribution history, pooled async connections, and PostGIS spatial indexes.
The p95 target still needs to be measured on representative staging data and
infrastructure; run the opt-in benchmark after deployment:

```powershell
$env:AGROSENSE_PERF_BASE_URL = "https://STAGING_API_HOST"
$env:AGROSENSE_PERF_TOKEN = "STAGING_ACCESS_TOKEN"
$env:AGROSENSE_PERF_LOT_ID = "LOT_UUID"
$env:AGROSENSE_PERF_FARM_ID = "FARM_UUID"
uv run --package agrosense-api pytest apps/api/tests/test_latency_sla.py
```

Run API contract and certification tests locally with:

```powershell
uv run --package agrosense-api pytest apps/api/tests
```
