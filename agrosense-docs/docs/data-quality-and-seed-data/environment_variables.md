# Seed Configuration Parameters & Environment Variables Specification

This document specifies all configurable inputs (Environment Variables and CLI flags) that control dataset volume, defect injection rates, agronomic alert scenarios, randomness, and execution behavior for the **AgroSense Café** seed engine (**Deliverable E-03**, **Acceptance Criteria CT-01, CT-02, CT-06**).

---

## 1. Configuration Architecture & Precedence Hierarchy

To ensure the seed process can adapt across local development, CI/CD pipelines, and AWS production without modifying Python source code, configuration values are resolved following a strict **3-level precedence hierarchy**:

1. **Level 1 (Highest Priority) — CLI Arguments:** Explicit flags passed at runtime (e.g., `--mode dev --defect-rate 0.15 --reset`).
2. **Level 2 (Medium Priority) — Environment Variables (`.env`):** Variables loaded from the local `.env` file or container environment (Docker Compose / ECS Task Definition).
3. **Level 3 (Lowest Priority) — Default Constants:** Fallback safe defaults defined in the configuration schema (`prod` baseline).

> **Security Compliance (CT-02):** Database credentials and secrets are strictly injected via environment variables or AWS Secrets Manager. No passwords or API keys are hardcoded in source files or committed to Git.

---

## 2. Configurable Parameters Specification

### 2.1 Dataset Scale & Volume Parameters (Section 5.2)

Controls the number of records generated across operational tables and simulated raw files. Selecting `SEED_PROFILE=dev` automatically scales down volumes by 10x for fast local startup (under 30 minutes per **CT-01**).

| Environment Variable       | CLI Flag               | Type       | Default (`prod`) | Default (`dev`) | Description / Target Table                                            |
| :------------------------- | :--------------------- | :--------- | :----------------- | :---------------- | :-------------------------------------------------------------------- |
| `SEED_PROFILE`           | `--mode`             | `STRING` | `prod`           | `dev`           | Execution preset (`prod`, `dev`, `test`).                       |
| `SEED_FARMS_TOTAL`       | `--farms`            | `INT`    | `1300`           | `130`           | Total associated farms generated in`farms`.                         |
| `SEED_PILOT_FARMS_COUNT` | `--pilot-farms`      | `INT`    | `300`            | `30`            | Farms with`has_pilot_sensors = TRUE` (**F4**).                |
| `SEED_SENSORS_PER_FARM`  | `--sensors-per-farm` | `INT`    | `3`              | `3`             | Sensors per pilot farm (`SOIL_MOISTURE`, `TEMP`, `RAIN`).       |
| `SEED_TELEMETRY_DAYS`    | `--telemetry-days`   | `INT`    | `30`             | `7`             | Historical days of 10-min IoT readings & satellite data.              |
| `SEED_DELIVERIES_TOTAL`  | `--deliveries`       | `INT`    | `15000`          | `1500`          | Annual coffee deliveries in`harvest_deliveries` (**F5**).     |
| `SEED_EXPORT_BATCHES`    | `--batches`          | `INT`    | `500`            | `50`            | Consolidated export lots in`export_batches`.                        |
| `SEED_SOIL_ANALYSES_MO`  | `--soil-monthly`     | `INT`    | `100`            | `15`            | Monthly lab reports generated in`soil_lab_analyses` (**F6**). |
| `SEED_BUYERS_TOTAL`      | `--buyers`           | `INT`    | `40`             | `10`            | International buyers in`international_buyers` (**F7**).       |

---

### 2.2 Data Quality Defect Injection Parameters (Section 5.3 & Business Rules)

Controls the deliberate injection of dirty data and hardware anomalies required to validate pipeline resilience and business rules (**RN-01** to **RN-11**). All rates are expressed as floats between `0.0` (0%) and `1.0` (100%).

| Environment Variable                 | CLI Flag                | Type      | Default  | Target Defect / Business Rule & Acceptance Criterion                                                 |
| :----------------------------------- | :---------------------- | :-------- | :------- | :--------------------------------------------------------------------------------------------------- |
| `SEED_DEFECT_GLOBAL_RATE`          | `--defect-rate`       | `FLOAT` | `0.05` | Master fallback rate (5%) if specific defect rates are unset.                                        |
| `SEED_DEFECT_CLOCK_DRIFT_RATE`     | `--clock-drift-rate`  | `FLOAT` | `0.05` | Sensors reporting timestamps shifted by several hours (**Sec 5.3, RN-01**).                    |
| `SEED_DEFECT_STUCK_SENSOR_RATE`    | `--stuck-sensor-rate` | `FLOAT` | `0.03` | Sensors reporting less than 0.5% variation for more than 24 hours (**Sec 5.3, RN-02, CA-02**). |
| `SEED_DEFECT_DISCONNECT_RATE`      | `--disconnect-rate`   | `FLOAT` | `0.10` | Sensors losing cellular signal and sending delayed blocks (**RNF-01, CA-01**).                 |
| `SEED_MAX_DISCONNECT_DAYS`         | `--max-delay-days`    | `INT`   | `7`    | Maximum accumulated days in a reconnected IoT block (`1` to `7` days — **RNF-01**).       |
| `SEED_DEFECT_BAD_COORDS_RATE`      | `--bad-coords-rate`   | `FLOAT` | `0.02` | Farms with inverted`lat`/`lon` or out-of-country coordinates (**Sec 5.3**).                |
| `SEED_DEFECT_MIXED_UNITS_RATE`     | `--mixed-units-rate`  | `FLOAT` | `0.25` | Soil lab reports mixing`ppm`, `mg/kg`, `%`, and `g/kg` (**Sec 5.3, CA-06**).           |
| `SEED_DEFECT_UNLINKED_FARM_RATE`   | `--unlinked-rate`     | `FLOAT` | `0.04` | Deliveries/batches with`farm_id = NULL` blocking export (**Sec 5.3, RN-08, CA-07**).         |
| `SEED_DEFECT_RESERVE_OVERLAP_RATE` | `--overlap-rate`      | `FLOAT` | `0.03` | Farms overlapping protected`forest_reserves` blocking certification (**RN-09, CA-08**).      |

---

### 2.3 Forced Agronomic Alert Scenarios (Deterministic Test Cases)

Guarantees that specific farms meet the exact meteorological and soil thresholds required to verify acceptance criteria **CA-03**, **CA-04**, and **CA-05**.

| Environment Variable              | CLI Flag              | Type    | Default | Forced Scenario Description                                                                                                                               |
| :-------------------------------- | :-------------------- | :------ | :------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SEED_FORCE_ROYA_FARMS`         | `--force-roya`      | `INT` | `15`  | Forces 4 or more consecutive days with relative humidity above 85% (at least 6 hours/day) and temperatures between 21 and 25°C (**RN-03, CA-03**). |
| `SEED_FORCE_DEFICIT_FARMS`      | `--force-deficit`   | `INT` | `10`  | Forces 5 days with soil moisture below 25% and a 5-day rain forecast of at most 5 mm (**RN-04**).                                                   |
| `SEED_FORCE_DEFICIT_CANCEL`     | `--force-rain-save` | `INT` | `5`   | Forces dry soil (below 25%) but injects an 8 mm rain forecast to verify alert cancellation (**CA-04**).                                             |
| `SEED_FORCE_EXTREME_RAIN_FARMS` | `--force-rain`      | `INT` | `8`   | Forces accumulated precipitation above 120 mm within a 72-hour window (**RN-05**).                                                                  |

---

### 2.4 Execution Behavior & Reproducibility Parameters

Controls PRNG seeding, cleanup behavior, and database batching performance.

| Environment Variable         | CLI Flag          | Type       | Default   | Description                                                                                          |
| :--------------------------- | :---------------- | :--------- | :-------- | :--------------------------------------------------------------------------------------------------- |
| `SEED_RANDOM_STATE`        | `--seed`        | `INT`    | `42`    | Fixed integer seed for`random`, `numpy`, `Faker`, and `UUIDv5` generation (**CT-06**). |
| `SEED_RESET_BEFORE_RUN`    | `--reset`       | `BOOL`   | `false` | Executes`TRUNCATE ... RESTART IDENTITY CASCADE` before inserting if `true`.                      |
| `SEED_DB_BATCH_SIZE`       | `--batch-size`  | `INT`    | `1000`  | Number of rows per bulk`INSERT ... ON CONFLICT` chunk to optimize memory and I/O.                  |
| `SEED_OUTPUT_BRONZE_FILES` | `--emit-bronze` | `BOOL`   | `true`  | Generates raw JSON/CSV seed files for S3 Bronze / local landing zone (**F1–F4, F6**).         |
| `SEED_LOG_LEVEL`           | `--log-level`   | `STRING` | `INFO`  | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`).                                     |

---

### 2.5 Database & Storage Connection Variables (CT-02)

Required connection parameters injected via environment variables:

| Environment Variable    | Type       | Example (Local Docker)                | Description                                                    |
| :---------------------- | :--------- | :------------------------------------ | :------------------------------------------------------------- |
| `POSTGRES_HOST`       | `STRING` | `postgres-db` / `localhost`       | Database hostname or AWS RDS endpoint.                         |
| `POSTGRES_PORT`       | `INT`    | `5432`                              | PostgreSQL port.                                               |
| `POSTGRES_DB`         | `STRING` | `agrosense_db`                      | Target operational database name.                              |
| `POSTGRES_USER`       | `STRING` | `agrosense_user`                    | Database username with write privileges.                       |
| `POSTGRES_PASSWORD`   | `STRING` | *(Injected via `.env` / Secrets)* | Database password (Never committed to Git —**CT-02**).  |
| `BRONZE_LANDING_PATH` | `STRING` | `./data/bronze` or `s3://...`     | Destination URI for simulated raw files (IoT JSONs, Lab CSVs). |

---

## 3. Reference `.env.example` Template

This template is versioned at the root of the repository as `.env.example`. Developers copy it to `.env` (which is ignored via `.gitignore`) to customize their local execution:

```ini
# =====================================================================
# AGROSENSE CAFÉ — SEED & ENVIRONMENT CONFIGURATION (.env.example)
# =====================================================================

# --- 1. Database Connection (PostgreSQL) ---
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=agrosense_db
POSTGRES_USER=agrosense_admin
POSTGRES_PASSWORD=change_me_in_local_env_only

# --- 2. Storage & Landing Zone ---
BRONZE_LANDING_PATH=./data/lake/bronze

# --- 3. Execution Behavior & Reproducibility (CT-06) ---
SEED_PROFILE=prod
SEED_RANDOM_STATE=42
SEED_RESET_BEFORE_RUN=false
SEED_DB_BATCH_SIZE=1000
SEED_OUTPUT_BRONZE_FILES=true
SEED_LOG_LEVEL=INFO

# --- 4. Dataset Volume & Scale (Section 5.2) ---
SEED_FARMS_TOTAL=1300
SEED_PILOT_FARMS_COUNT=300
SEED_SENSORS_PER_FARM=3
SEED_TELEMETRY_DAYS=30
SEED_DELIVERIES_TOTAL=15000
SEED_EXPORT_BATCHES=500
SEED_SOIL_ANALYSES_MO=100
SEED_BUYERS_TOTAL=40

# --- 5. Data Quality Defect Injection Rates (Section 5.3) ---
SEED_DEFECT_GLOBAL_RATE=0.05
SEED_DEFECT_CLOCK_DRIFT_RATE=0.05
SEED_DEFECT_STUCK_SENSOR_RATE=0.03
SEED_DEFECT_DISCONNECT_RATE=0.10
SEED_MAX_DISCONNECT_DAYS=7
SEED_DEFECT_BAD_COORDS_RATE=0.02
SEED_DEFECT_MIXED_UNITS_RATE=0.25
SEED_DEFECT_UNLINKED_FARM_RATE=0.04
SEED_DEFECT_RESERVE_OVERLAP_RATE=0.03

# --- 6. Deterministic Agronomic Alert Scenarios (CA-03, CA-04, CA-05) ---
SEED_FORCE_ROYA_FARMS=15
SEED_FORCE_DEFICIT_FARMS=10
SEED_FORCE_DEFICIT_CANCEL=5
SEED_FORCE_EXTREME_RAIN_FARMS=8
```
