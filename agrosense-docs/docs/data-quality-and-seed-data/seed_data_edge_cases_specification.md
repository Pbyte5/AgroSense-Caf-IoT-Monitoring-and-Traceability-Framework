# Seed Data Generation: Edge Cases & Boundary Scenarios Specification

| **Document Metadata:** Technical Specification & Quality Validation Framework  **Project Scope:** AgroSense Café — IoT Telemetry & Agroclimatic Traceability Platform  **Purpose:** Defines mandatory anomaly injection, agronomic threshold boundaries, idempotency constraints, and security isolation tests for seed data generation. |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
|                                                                                                                                                                                                                                                                                                                                                              |

## 1. Executive Summary & Testing Framework

The seed data generator for the AgroSense Café platform serves a dual
function: populating development and testing environments with realistic
domain records and rigorously testing the platform's distributed data
pipelines, business rules, and security controls. Rather than generating
purely synthetic nominal datasets, the engine explicitly incorporates
edge cases, boundary scenarios, and controlled defect injections.

By validating system behavior against these boundary conditions across
all 5 topological storage tiers—from transactional PostgreSQL tables to
the Medallion Data Lake layers (Bronze, Silver, Gold)—the development
team guarantees that data corruption, network outages, and edge
agronomic states are gracefully handled without compromising platform
stability or analytical integrity.

## 2. Controlled Data Quality Defects & Anomaly Injections

The seed generator intentionally injects specific data anomalies
controlled via the **SEED_DEFECT_GLOBAL_RATE** environment variable.
These defects test the resilience of ingestion pipelines, Silver-layer
cleaning jobs, and automated error logging routines.

### 2.1 Clock Drift in Telemetry Stream (Desfase de Reloj)

- **Scenario Configuration:** Telemetry payloads generated with
  timestamps offset by several hours relative to the current UTC
  execution time.
- **Technical Mechanism:** Adjusts device payload timestamps beyond
  nominal transmission windows.
- **Validation Objective:** Evaluates the Silver layer timestamp
  normalization job and validates compliance with Business Rule RN-01,
  which requires telemetry readings to fall within a ±15-minute window
  after clock drift compensation.

### 2.2 Stuck / Frozen Sensor Stream (Sensor Congelado)

- **Scenario Configuration:** Environmental sensors reporting physical
  values (e.g., ambient temperature or soil moisture) with less than
  0.5% total variation across a continuous 24-hour observation window.
- **Technical Mechanism:** Simulates mechanical or electrical failure on
  IoT edge devices.
- **Validation Objective:** Verifies automated entry creation in
  sensor_anomalies_log, flagging device status as DEFECTIVE_STUCK, and
  excluding frozen stream metrics from downstream agronomic alert
  calculation models (RN-02, CA-02, RF-08).

**2.3 Cellular Disconnection & Bulk Delayed Telemetry (Bloques
Retrasados)**

- **Scenario Configuration:** Simulates rural connectivity outages
  lasting between 1 and 7 days (RNF-01). Edge nodes queue readings
  locally and transmit accumulated multi-day payload blocks upon network
  re-establishment.
- **Technical Mechanism:** Injects out-of-order and multi-day historical
  telemetry batches into the RabbitMQ ingestion queues.
- **Validation Objective:** Tests out-of-order processing pipelines,
  confirming that historical batches are correctly partitioned,
  chronological sequence is preserved, and duplicate records are
  prevented (CA-01).

### 2.4 Inverted and Out-of-Range Geocoordinates (Coordenadas Erróneas)

- **Scenario Configuration:** Farm registration entities containing
  swapped latitude/longitude coordinates or spatial polygon geometries
  located outside recognized national coffee-growing regions.
- **Technical Mechanism:** Generates spatial coordinates outside valid
  bounding boxes or with reversed coordinate order.
- **Validation Objective:** Validates spatial validation pipelines,
  verifying that invalid geographic entries correctly set the flag
  has_valid_coords = FALSE and prevent automated geographic clustering
  errors.

### 2.5 Heterogeneous Soil Analysis Measurement Units

- **Scenario Configuration:** Soil laboratory reports (Form F6)
  containing mixed unit conventions across samples (alternating between
  ppm, mg/kg, %, and g/kg).
- **Technical Mechanism:** Injects unstandardized laboratory result
  formats into the raw ingestion layer.
- **Validation Objective:** Ensures mandatory Silver-layer unit
  normalization to standard mg/kg units (CA-06), proving that identical
  chemical nutrient levels result in equal fertilization recommendations
  (RN-07).

### 2.6 Unlinked Harvest Delivery Records (Entregas Sin Finca)

- **Scenario Configuration:** Coffee harvest delivery batches or lot
  composition records with farm_id = NULL or pointing to unregistered
  farm entities.
- **Technical Mechanism:** Orphaned delivery entries injected into the
  supply chain ingestion queue.
- **Validation Objective:** Validates digital supply chain traceability
  rules by immediately revoking export eligibility and setting
  is_exportable = FALSE for affected export lots (RN-08, CA-07).

### 2.7 Forest Reserve Overlaps (Solapamiento con Reservas)

- **Scenario Configuration:** Farm perimeter polygon boundaries
  intersecting designated protected forest reserve areas
  (farm_reserve_overlaps).
- **Technical Mechanism:** Spatial intersection between farm boundary
  spatial data and environmental reserve shapefiles.
- **Validation Objective:** Confirms the automatic revocation of
  environmental sustainability credentials (is_certified = FALSE) and
  rejects farm contributions from certified export coffee batches
  (RN-09, CA-08).

## 3. Agronomic Boundary Scenarios & Decision Limits

To ensure absolute precision in automated agronomic decision-making, the
seed data generator creates forced boundary conditions that hit exact
threshold values specified in business rules.

### 3.1 Coffee Rust (Roya) Disease Warning Thresholds

- **Positive Boundary Scenario:** Weather telemetry maintaining relative
  humidity \> 85% for exactly 6 hours per day over 4 consecutive days,
  with average temperatures held strictly between 21°C and 25°C (RN-03,
  CA-03).
- **Negative Boundary Scenario:** Environmental conditions meeting
  temperature and humidity criteria for 3 consecutive days, but
  interrupted on Day 4 by a drop in relative humidity below 80%.
- **Validation Objective:** Confirms that the rust prediction model
  fires an early warning alert exactly on Day 4 for the positive
  scenario while producing zero false positives for the negative
  scenario.

### 3.2 Hydric Deficit Alert Suppression via Weather Forecast

- **Boundary Scenario:** Soil moisture telemetry reporting levels below
  25% for 5 consecutive days, coupled with a 5-day predictive weather
  forecast indicating 8 mm of accumulated precipitation (exceeding the 5
  mm threshold).
- **Validation Objective:** Verifies that the alert engine suppresses or
  cancels the drought warning based on forecasted rainfall, avoiding
  unnecessary irrigation dispatch (RN-04, CA-04).

### 3.3 Extreme Rainfall Accumulation Thresholds

- **Boundary Scenario:** Pluviometric data hitting exactly 120 mm of
  accumulated rainfall within a 72-hour sliding window.
- **Validation Objective:** Verifies the immediate execution of extreme
  rainfall warning protocols and landslide risk notifications (RN-05).

### 3.4 Agronomist Visit Priority Scoring & Tie-Breaking Matrix

- **Boundary Scenario:** Multiple member farms producing identical
  priority scores using the multi-factor scoring formula:
  | **Agronomic Priority Score Formula:** Priority = (3 × Rust\_Alert) + (2 × Deficit\_Alert) + (1 × Rain\_Alert)  **Tie-Breaking Criterion:** In the event of identical priority scores, tie-breaking must prioritize farms with larger cultivated surface areas (cultivated\_area\_ha). |
  | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
  |                                                                                                                                                                                                                                                                                                      |
- **Validation Objective:** Validates that the visit scheduling
  algorithm deterministically breaks ties by assigning technical advisor
  visits to larger farms first (RN-06, CA-05).

### 3.5 Minimum Contribution Batch Traceability

- **Boundary Scenario:** Commercial export batches containing coffee
  contributions from member farms representing less than 5% of total
  batch weight.
- **Validation Objective:** Guarantees that minor farm contributions are
  preserved in full digital traceability ledgers without being truncated
  or filtered out by thresholding errors (RN-08).

## 4. Idempotency, Uniqueness & Database Integrity Controls

The seed generation architecture mandates complete deterministic
execution. Running the seeding script multiple times against the target
database must produce an identical system state without duplicate key
errors or orphan rows.

### 4.1 Deterministic State Engine

- **Fixed Seed State:** Utilizes a fixed Pseudorandom Number Generator
  (PRNG) state (SEED_RANDOM_STATE=42) combined with deterministic UUIDv5
  namespace generation.
- **UPSERT Logic:** All database insertions leverage PostgreSQL INSERT
  ... ON CONFLICT clauses targetting natural keys to seamlessly perform
  in-place updates (UPSERT) without key violation failures (CT-06).

### 4.2 Topological Tier Loading Order

To eliminate foreign key constraint violations during batch ingestion,
the seed generator executes data loading strictly across 5 sequential
dependency tiers:

| \# Tier\*\*      | **Layer / Domain**    | \*\*Entities Loaded                                                     |
| :--------------- | :-------------------------- | :---------------------------------------------------------------------- |
| **Tier 1** | Core Reference Data         | Departments, Municipalities, Cooperatives, Buyer Profiles, System Roles |
| **Tier 2** | Producer & Spatial Entities | Farmers, Farm Boundaries, Parcels, Forest Reserves, Soil Test Labs      |
| **Tier 3** | Hardware & Batches          | IoT Weather Stations, Sensor Nodes, Harvest Batches, Buyer Contracts    |
| **Tier 4** | Telemetry & Operations      | Environmental Telemetry Streams, Harvest Deliveries, Soil Analyses      |
| **Tier 5** | Aggregates & Audits         | Agronomic Alerts, Technical Visit Schedules, Buyer Audit Logs           |

### 4.3 Atomic Schema Reset Mode (--reset)

When executed with the **--reset** CLI flag, the seed engine performs an
atomic schema cleanup using **TRUNCATE TABLE ... RESTART IDENTITY
CASCADE** inside a single database transaction. This guarantees instant
recovery to a clean state from corrupted local environments.

## 5. Security & Multi-Tenant Isolation Testing

### 5.1 Unauthorized Buyer Batch Access

- **Scenario Configuration:** Generates buyer contracts
  (buyer_batch_contracts) and attempts cross-tenant traceability queries
  where Commercial Buyer A requests internal farm data for a batch
  purchased by Commercial Buyer B (RN-11, RNF-06).
- **Validation Objective:** Validates that the REST API layer enforces
  strict tenant boundaries, returning HTTP 403 Forbidden while
  generating an audit event in buyer_api_audit_logs (CA-09).

## 6. Comprehensive Validation Matrix

The following matrix summarizes all edge cases, expected system
behaviors, and corresponding business rule references for developer
validation:

| \# Scenario Name\*\*            | **Category** | **Expected System Behavior**                          | \*\*Rule Ref. |
| ------------------------------- | :----------------- | :---------------------------------------------------------- | :------------ |
| **Clock Drift**           | Data Quality       | Timestamps corrected in Silver layer within ±15 min window | RN-01         |
| **Stuck Sensor**          | Hardware Fault     | Log in sensor_anomalies_log; flag DEFECTIVE_STUCK           | RN-02, CA-02  |
| **Delayed IoT Blocks**    | Network Outage     | Batch ingestion preserving strict chronological order       | CA-01, RNF-01 |
| **Bad Coordinates**       | Spatial Data       | Set has_valid_coords = FALSE; exclude from spatial maps     | Geospatial    |
| **Mixed Soil Units**      | Data Quality       | Standardize units to mg/kg; calculate correct fertilizer    | RN-07, CA-06  |
| **Unlinked Deliveries**   | Traceability       | Invalidate export lot; set is_exportable = FALSE            | RN-08, CA-07  |
| **Reserve Overlaps**      | Compliance         | Revoke sustainability badge; is_certified = FALSE           | RN-09, CA-08  |
| **Rust Threshold (4d)**   | Agronomic Alert    | Trigger Rust early warning alert on Day 4 exactly           | RN-03, CA-03  |
| **Hydric Deficit / Rain** | Agronomic Alert    | Suppress drought alert if forecast\> 5mm rain               | RN-04, CA-04  |
| **Unauthorized Buyer**    | Security           | Deny access with HTTP 403; write to audit log               | RN-11, CA-09  |
