# AgroSense Café — Seed Reproducibility & Strategy Specification

Deterministic Dataset Generation, UUIDv5 Mapping, UPSERT Policies, and
Topological Ingestion Order

# 1. Executive Summary & Strategy Overview

The AgroSense Café seed generation engine guarantees 100% deterministic,
reproducible, and idempotent dataset population across local development
(Docker Compose) and AWS cloud environments (RDS PostgreSQL). Running
the seeding process once, twice, or multiple times with identical
configuration parameters produces exact state convergence without
primary key collisions, foreign key violations, or duplicate records
(Deliverable E-03, Acceptance Criteria CT-01, CT-02, CT-06).

To achieve complete repeatability across farms, cultivation plots,
harvest deliveries, export batches, and IoT telemetry streams, the
architecture enforces four foundational pillars:

- **Fixed PRNG State:** Global initialization of Pseudo-Random Number
  Generators (random, numpy, Faker) using a fixed integer seed
  (SEED_RANDOM_STATE = 42).

- **Deterministic Primary Keys (UUIDv5):** Derivation of UUID primary
  keys using SHA-1 namespace hashing on natural business keys,
  eliminating non-deterministic UUIDv4 generation.

- **PostgreSQL UPSERT Policies (ON CONFLICT):** Database-level
  idempotency enforced via ON CONFLICT (natural_key) DO UPDATE or DO
  NOTHING clauses on all operational tables.

- **Topological 5-Tier Ingestion Order:** Strict sequential dependency
  resolution ensuring parent records exist before dependent foreign keys
  are populated.

# 2. Deterministic Identifiers & Fixed PRNG State

Randomness in synthetic data generation can cause subtle discrepancies
across environments. To prevent state divergence, the seed module
establishes a strict seed initialization protocol before instantiating
any data generation logic.

## 2.1 PRNG Initialization

At runtime, the Python process locks all pseudo-random generators to the
value specified by **SEED_RANDOM_STATE** (default: 42):

import random  
import numpy as np  
from faker import Faker  
  
def set_reproducible_state(seed: int = 42):  
random.seed(seed)  
np.random.seed(seed)  
Faker.seed(seed)  
os.environ\['PYTHONHASHSEED'\] = str(seed)

## 2.2 Deterministic UUIDv5 Identifier Mapping

Standard UUIDv4 identifiers rely on random bits, which generate
different primary keys every time a seed script executes. AgroSense Café
replaces random UUIDs with UUIDv5, generating deterministic 128-bit
values by hashing a static project namespace (AGROSENSE_NAMESPACE =
uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')) together with natural
entity business keys.

| **Domain Entity**       | **Target Primary Key** | **Natural Key Expression**                  | **Deterministic Output Example** |
|:------------------------|:-----------------------|:--------------------------------------------|:---------------------------------|
| farms                   | farm_id (UUID)         | farm_code (e.g., 'FIN-0001')                | e7a3b110-...                     |
| farm_plots              | plot_id (UUID)         | farm_code + ':' + plot_name                 | 8f12c49a-...                     |
| producers               | producer_id (UUID)     | document_number (e.g., 'CC-109823')         | 3c4901ea-...                     |
| international_buyers    | buyer_id (UUID)        | client_id (e.g., 'BUY-EU-001')              | a190f842-...                     |
| soil_lab_analyses       | analysis_id (UUID)     | farm_code + ':' + sample_date               | b881d332-...                     |
| harvest_deliveries      | delivery_id (UUID)     | farm_code + ':' + delivery_date + ':' + seq | 190f77bc-...                     |
| export_batches          | batch_id (UUID)        | batch_code (e.g., 'EXP-2026-0001')          | d441e890-...                     |
| batch_farm_compositions | composition_id (UUID)  | batch_code + ':' + delivery_id              | 45a9018f-...                     |
| buyer_batch_contracts   | contract_id (UUID)     | batch_code + ':' + client_id                | ef11c900-...                     |

# 3. Database-Level Idempotency & UPSERT Policy (ON CONFLICT)

Deterministic primary keys prevent duplicate ID generation, but
re-running the seed engine against a populated database will result in
unique constraint violations unless SQL statements explicitly define
conflict resolution behaviors. Every SQL insertion executed by the seed
generator utilizes PostgreSQL **INSERT ... ON CONFLICT** clauses mapped
to unique business keys (Acceptance Criterion CT-06).

| **Target Table**        | **Unique Natural Key Target** | **Conflict Strategy** | **Updated Attributes on Conflict**        |
|:------------------------|:------------------------------|:----------------------|:------------------------------------------|
| departments             | ON CONFLICT (dane_code)       | **DO NOTHING**        | Static reference catalog.                 |
| municipalities          | ON CONFLICT (dane_code)       | **DO NOTHING**        | Static geographic catalog.                |
| users                   | ON CONFLICT (email)           | **DO UPDATE**         | full_name, role, password_hash.           |
| producers               | ON CONFLICT (document_number) | **DO UPDATE**         | full_name, phone_number.                  |
| international_buyers    | ON CONFLICT (client_id)       | **DO UPDATE**         | company_name, country, api_key_hash.      |
| farms                   | ON CONFLICT (farm_code)       | **DO UPDATE**         | latitude, longitude, total_area, polygon. |
| farm_plots              | ON CONFLICT (plot_id)         | **DO UPDATE**         | plot_area_ha, crop_age_years.             |
| iot_sensors             | ON CONFLICT (serial_number)   | **DO UPDATE**         | health_status, battery_level, last_tx.    |
| soil_lab_analyses       | ON CONFLICT (analysis_id)     | **DO UPDATE**         | nitrogen, phosphorus, potassium, pH.      |
| harvest_deliveries      | ON CONFLICT (delivery_id)     | **DO UPDATE**         | delivered_weight_kg, moisture_pct.        |
| export_batches          | ON CONFLICT (batch_code)      | **DO UPDATE**         | traced_weight_kg, is_exportable.          |
| batch_farm_compositions | ON CONFLICT (composition_id)  | **DO NOTHING**        | Immutable composition bridge.             |
| buyer_batch_contracts   | ON CONFLICT (contract_id)     | **DO UPDATE**         | purchase_date, shipping_container_id.     |

# 4. Topological Insertion Order (5 Sequential Tiers)

Foreign key constraints require child records to refer strictly to
existing parent keys. To maintain referential integrity without
disabling database constraints or triggering foreign key violations
during execution, the seed engine populates the relational schema in a
strict 5-tier topological sequence:

- **Tier 1 — Independent Master Catalogs & Actors:** departments, users,
  producers, international_buyers, coffee_varieties, sensor_types,
  crop_nutrient_references (Source F1 Kaggle reference). These tables
  have zero external foreign key dependencies.

- **Tier 2 — Spatial & Regional Entities:** municipalities (depends on
  departments), forest_reserves (depends on municipalities). Establishes
  regional boundaries and protected reserve geometries.

- **Tier 3 — Core Agricultural Entities:** farms (depends on producers &
  municipalities), farm_plots (depends on farms & coffee_varieties),
  farm_reserve_overlaps (depends on farms & forest_reserves). Defines
  farm geometries and pilot IoT flags.

- **Tier 4 — Operational, Hardware & Field Data:** iot_sensors (depends
  on farms & sensor_types), sensor_anomalies_log, soil_lab_analyses
  (Source F6, depends on farms), fertilizer_recommendations,
  harvest_deliveries (Source F5, depends on farms).

- **Tier 5 — Aggregations, Traceability & Alert Outputs:**
  export_batches, batch_farm_compositions (depends on batches &
  deliveries), cupping_evaluations, buyer_batch_contracts (depends on
  batches & buyers), agronomic_alerts, agronomist_field_visits.

# 5. Configuration Profiles, Reset Mechanics & Verification

The seed engine supports two volume scale profiles to balance local
development speed with full production volume testing:

- **Production Profile (SEED_PROFILE=prod):** Generates 1,300 associated
  farms, 300 pilot sensor farms (900 total sensors), ~15,000 annual
  harvest deliveries, 500 export batches, and 40 international buyers as
  specified in Section 5.2 of the project specification.

- **Development Profile (SEED_PROFILE=dev):** Scales down volume by 10x
  (130 farms, 30 pilot farms, 1,500 deliveries, 50 batches) to enable
  rapid local environment startup (\< 30 minutes, CT-01).

## 5.1 Atomic Reset Execution (--reset)

When executing with the **--reset** flag (or
SEED_RESET_BEFORE_RUN=true), the seed generator executes a clean wipe
prior to population:

- **Atomic Database Transaction:** Encloses truncation and seeding in a
  single BEGIN ... COMMIT block with automatic ROLLBACK on error.

- **Cascading Truncation:** Executes TRUNCATE TABLE ... RESTART IDENTITY
  CASCADE across all operational tables to bypass foreign key lock
  errors cleanly.

- **Sequence Counter Reset:** Resets all auto-incrementing SERIAL
  counters (department_id, municipality_id, audit_id) back to 1.

## 5.2 Verification & Acceptance Criteria

To verify acceptance criterion **CT-06** (Zero Duplicates & Full
Repeatability), developers run the following verification protocol:

\# Step 1: Run seed in production mode  
uv run python -m scripts.seed --mode prod --seed 42 --reset  
  
\# Step 2: Record exact table row counts (e.g., SELECT COUNT(\*) FROM
farms -\> 1300)  
  
\# Step 3: Re-run seed WITHOUT reset (testing UPSERT idempotency)  
uv run python -m scripts.seed --mode prod --seed 42  
  
\# Step 4: Verify row counts remain EXACTLY identical with ZERO
duplicate keys

By combining fixed PRNG state, UUIDv5 deterministic mapping, ON CONFLICT
UPSERT clauses, and 5-tier topological ordering, the AgroSense Café seed
engine provides complete test dataset reproducibility across local and
cloud environments.
