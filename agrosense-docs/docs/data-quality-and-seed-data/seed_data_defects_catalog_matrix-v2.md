# Data Quality Defects Catalog & Injection Matrix

| **Document Purpose:** *This specification outlines the structured defect catalog and anomaly injection rules integrated into the AgroSense Café seed data generator. All injected defects test pipeline resilience, automated validation rules, and quarantine logging routines.* |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
|                                                                                                                                                                                                                                                                                            |

## 1. Overview & Resiliency Testing Objectives

In production IoT and agroclimatic data platforms, real-world data is
inherently noisy, incomplete, and occasionally malformed. To validate
that the AgroSense Café Data Lake (Medallion architecture) and
processing microservices react gracefully under error conditions, the
synthetic seed generator includes a dedicated Anomaly Injection Engine.

**Key Testing Goals:** By injecting controlled defects during seed
creation, engineering teams can verify that:

- **1. Pipeline Robustness:** The Silver Layer cleaning pipelines detect
  and adjust timestamps or quarantine invalid payloads.
- **2. Anomaly Logging:** Anomaly detection models set flags (e.g.,
  DEFECTIVE_STUCK) and log incidents into sensor_anomalies_log.
- **3. Alert Suppression:** Agronomic rule engines suppress alerts when
  sensors are flagged as stuck or out of range (RN-02, CA-02).
- **4. Compliance Enforcement:** Export batch certification rules reject
  unlinked deliveries or forest reserve overlaps (RN-08, RN-09).
- **5. Unit Normalization:** Heterogeneous laboratory soil measurement
  units are standardized to mg/kg prior to fertilization modeling
  (CA-06).

## 2. Defect Catalog & Injection Matrix

The matrix below summarizes the nine standardized defect types injected
by the seed generator. Injections are governed by the global parameter
SEED_DEFECT_GLOBAL_RATE (default 0.05 / 5%) and are fully deterministic
due to the fixed PRNG state (SEED_RANDOM_STATE=42).

| **Defect ID** | **Defect Name**  | **Target Entity & Fields**                  | **Default Rate** | **Target Pipeline & Business Rule**                                                       |
| ------------------- | ---------------------- | ------------------------------------------------- | ---------------------- | ----------------------------------------------------------------------------------------------- |
| **DEF-01**    | Clock Drift            | iot\_telemetries  (reading\_timestamp)            | 5%                     | Silver layer timestamp correction & ±15 min validation window (RN-01, CA-01).                  |
| **DEF-02**    | Stuck Sensor           | iot\_telemetries, iot\_sensors  (status, values)  | 3%                     | Logging in sensor\_anomalies\_log, status DEFECTIVE\_STUCK, alert exclusion (RN-02, CA-02).     |
| **DEF-03**    | Delayed IoT Blocks     | iot\_telemetries  (ingestion\_batch\_id)          | 10% nodes              | Cellular outage simulation (1-7 days). Out-of-order batch ingestion without duplicates (CA-01). |
| **DEF-04**    | Bad Coordinates        | farms  (latitude, longitude)                      | 2%                     | Spatial validation flagging invalid geometries with has\_valid\_coords = FALSE.                 |
| **DEF-05**    | Mixed Soil Units       | soil\_lab\_analyses  (nitrogen, phosphorus, etc.) | 15%                    | Mandatory unit standardization to mg/kg (CA-06) for fertilization model (RN-07).                |
| **DEF-06**    | Unlinked Deliveries    | harvest\_deliveries  (farm\_id)                   | 2%                     | Supply chain integrity enforcement. Invalidates export batch (is\_exportable = FALSE, RN-08).   |
| **DEF-07**    | Forest Reserve Overlap | farm\_reserve\_overlaps  (farm\_id, reserve\_id)  | 5% pilot               | Automatic revocation of sustainability credentials (is\_certified = FALSE, RN-09).              |
| **DEF-08**    | Out-of-Range Data      | iot\_telemetries  (temperature, humidity)         | 1%                     | Silver layer boundary filtering (temp > 65°C, humidity < 0%) and quarantine logging.           |
| **DEF-09**    | Duplicate Payloads     | iot\_telemetries  (sensor\_id, timestamp)         | 3%                     | Message queue deduplication testing using PostgreSQL UPSERT and RabbitMQ (CT-06).               |

## 3. Detailed Defect Injection Specifications

### 3.1 Clock Drift (DEF-01)

Telemetry readings are generated with a timestamp offset ranging from -2
hours to +12 hours relative to the actual transmission time.

- **Scope:** Target Entity: iot_telemetries (reading_timestamp).
- **Purpose:** Simulates unsynchronized internal clocks on remote IoT
  microcontrollers due to power loss.
- **Validation Rule:** The Silver layer ETL pipeline must calculate the
  drift against the ingestion_timestamp, apply time correction, and
  validate that the corrected timestamp falls within a ±15-minute window
  (RN-01, CA-01).

### 3.2 Stuck Sensor Anomaly (DEF-02)

A sensor's reported values remain nearly static, varying by less than
0.5% over a continuous 24-hour observation period.

- **Scope:** Target Entity: iot_telemetries, iot_sensors.
- **Purpose:** Simulates physical sensor failure, debris coverage, or
  frozen analog-to-digital converters.
- **Validation Rule:** The anomaly detection worker logs an incident
  into sensor_anomalies_log, updates the sensor status to
  DEFECTIVE_STUCK, and excludes its readings from agronomic alert models
  (RN-02, CA-02).

### 3.3 Delayed IoT Block Ingestion (DEF-03)

Edge nodes accumulate telemetry locally during cellular connectivity
outages lasting between 1 and 7 days (RNF-01). Upon reconnection,
readings are transmitted in a single bulk payload.

- **Scope:** Target Entity: iot_telemetries (ingestion_batch_id).
- **Purpose:** Tests queue throughput, out-of-order timestamp sorting,
  and batch idempotency.
- **Validation Rule:** The ingestion service must process the entire
  block in chronological order without dropping records or triggering
  false duplicate errors (CA-01).

### 3.4 Bad Geographic Coordinates (DEF-04)

Farms registered with inverted latitude/longitude coordinates or
geographic points situated outside national coffee-producing zones.

- **Scope:** Target Entity: farms (latitude, longitude).
- **Purpose:** Validates spatial boundaries and GIS data sanity
  checking.
- **Validation Rule:** The spatial pipeline flags the farm with
  has_valid_coords = FALSE, preventing inclusion in regional GIS map
  layers until corrected.

### 3.5 Mixed Soil Laboratory Units (DEF-05)

Soil test reports (Kaggle F6 dataset) containing non-standard
measurement units, alternating between ppm, mg/kg, %, and g/kg across
different nutrient samples.

- **Scope:** Target Entity: soil_lab_analyses (nitrogen, phosphorus,
  potassium, organic_matter).
- **Purpose:** Tests data normalization and ETL transformation routines.
- **Validation Rule:** The ingestion pipeline converts all measurements
  to mg/kg (CA-06). Equivalent soil samples must produce identical
  fertilization recommendations regardless of input unit (RN-07).

### 3.6 Unlinked Harvest Deliveries (DEF-06)

Coffee harvest delivery receipts or batch composition items created with
farm_id = NULL or pointing to a non-existent farm record.

- **Scope:** Target Entity: harvest_deliveries (farm_id).
- **Purpose:** Validates supply chain integrity and digital traceability
  rules.
- **Validation Rule:** Unlinked deliveries invalidate the export
  certification for any lot that includes them, forcing is_exportable =
  FALSE (RN-08, CA-07).

### 3.7 Forest Reserve Overlap (DEF-07)

Farm polygon boundaries that geographically intersect with protected
forest reserves (farm_reserve_overlaps).

- **Scope:** Target Entity: farm_reserve_overlaps, farms.
- **Purpose:** Tests compliance with international environmental and
  deforestation regulations.
- **Validation Rule:** Automatically revokes sustainability
  certification (is_certified = FALSE) and rejects farm contributions to
  certified export batches (RN-09, CA-08).

## 4. Global Operational Controls

To allow flexible execution across development, testing, and CI/CD
environments, defect injection is controlled through environment
variables defined in environment_variables.md:

- **Master Rate:** SEED_DEFECT_GLOBAL_RATE: Master float multiplier (0.0
  to 1.0). Setting to 0.0 disables all defect injection for clean
  baseline testing.
- **PRNG Determinism:** SEED_RANDOM_STATE: Fixed integer seed (42)
  ensuring exact repetition of defect locations across re-runs.
- **Selective Defect Toggle:** SEED_INJECT_STUCK_SENSORS: Boolean flag
  (true/false) to specifically enable/disable stuck sensor simulation.
  | **Testing Best Practice:** *When running in zero-defect mode (SEED\_DEFECT\_GLOBAL\_RATE=0.0), the seed generator produces 100% compliant data ideal for performance benchmarking and baseline dashboard testing.* |
  | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
  |                                                                                                                                                                                                                            |
