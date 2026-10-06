# 🌱 AgroSense Café — Idempotent Seed Execution & Reset Specification

This specification defines the deterministic generation, uniqueness handling, cleanup/reset mechanics, and expected database states for the **AgroSense Café** data seeding process (**Deliverable E-03**, **Acceptance Criterion CT-06**).

---

## 1. Uniqueness Handling & Idempotency Strategy

Running the seed script once or multiple times with the same seed parameter must produce the **exact same dataset without duplicating rows or raising primary/foreign key errors** (**CT-06**).

### 1.1 Deterministic Generation (`Fixed Seed`)
* **PRNG Seeding:** All random generators (`random`, `numpy`, `Faker`) are initialized with a fixed seed (`DEFAULT_SEED = 42`).
* **Deterministic UUIDs (`UUIDv5`):** Instead of random `UUIDv4`, all primary keys of type `UUID` are generated deterministically using `uuid.uuid5(AGROSENSE_NAMESPACE, natural_key)`. For example, `FIN-0001` always resolves to the exact same `farm_id` across executions.

### 1.2 Natural Unique Keys & `UPSERT` (`ON CONFLICT`) Policy
Every operational table enforces idempotency at the database engine level using PostgreSQL `INSERT ... ON CONFLICT` clauses mapped to natural business keys:

| Domain | Table Name | Conflict Target (`UNIQUE` Key) | Conflict Action (`UPSERT`) |
| :--- | :--- | :--- | :--- |
| **Geography** | `departments` | `dane_code` | `ON CONFLICT (dane_code) DO NOTHING` |
| **Geography** | `municipalities` | `dane_code` | `ON CONFLICT (dane_code) DO NOTHING` |
| **Geography** | `forest_reserves` | `reserve_id` (UUIDv5 from name) | `ON CONFLICT (reserve_id) DO UPDATE` |
| **Security & Actors** | `users` | `email` | `ON CONFLICT (email) DO UPDATE` |
| **Security & Actors** | `producers` | `document_number` | `ON CONFLICT (document_number) DO UPDATE` |
| **Security & Actors** | `international_buyers` | `client_id` | `ON CONFLICT (client_id) DO UPDATE` |
| **Farms & Crops** | `coffee_varieties` | `name` | `ON CONFLICT (name) DO NOTHING` |
| **Farms & Crops** | `farms` | `farm_code` (e.g., `FIN-0001`) | `ON CONFLICT (farm_code) DO UPDATE` |
| **Farms & Crops** | `farm_plots` | `plot_id` (UUIDv5: `farm_code + plot_name`) | `ON CONFLICT (plot_id) DO UPDATE` |
| **IoT Hardware** | `sensor_types` | `type_code` | `ON CONFLICT (type_code) DO NOTHING` |
| **IoT Hardware** | `iot_sensors` | `serial_number` | `ON CONFLICT (serial_number) DO UPDATE` |
| **Soil & Nutrition** | `crop_nutrient_references` | `reference_id` (Row index from F1 CSV) | `ON CONFLICT (reference_id) DO NOTHING` |
| **Soil & Nutrition** | `soil_lab_analyses` | `analysis_id` (UUIDv5: `farm_code + sample_date`) | `ON CONFLICT (analysis_id) DO UPDATE` |
| **Traceability** | `harvest_deliveries` | `delivery_id` (UUIDv5: `farm_code + date + seq`) | `ON CONFLICT (delivery_id) DO UPDATE` |
| **Traceability** | `export_batches` | `batch_code` (e.g., `EXP-2026-0001`) | `ON CONFLICT (batch_code) DO UPDATE` |
| **Traceability** | `batch_farm_compositions` | `composition_id` (UUIDv5: `batch_code + delivery_id`)| `ON CONFLICT (composition_id) DO NOTHING` |
| **Traceability** | `buyer_batch_contracts` | `contract_id` (UUIDv5: `batch_code + client_id`) | `ON CONFLICT (contract_id) DO UPDATE` |

---

## 2. Cleanup, Reset Behavior & Topological Execution Order

### 2.1 Reset Mode (`--reset`)
When the `--reset` flag is passed, the seeding engine cleans the database before inserting fresh records:
1. **Atomic Transaction:** The entire cleanup and seeding workflow runs inside a single database transaction (`BEGIN ... COMMIT` with automatic `ROLLBACK` on failure).
2. **Safe Truncation (`TRUNCATE CASCADE`):** Executes `TRUNCATE TABLE ... RESTART IDENTITY CASCADE` across all operational tables to bypass foreign key lock errors cleanly.
3. **Sequence Reset (`RESTART IDENTITY`):** Resets all auto-incrementing counters (`SERIAL` / `BIGSERIAL` in `departments`, `municipalities`, `coffee_varieties`, `sensor_types`, `crop_nutrient_references`, and `buyer_api_audit_logs`) back to `1`.

### 2.2 Topological Insertion Order (Respecting Foreign Keys)
To guarantee 100% referential integrity during insertion, tables are populated strictly in 5 sequential tiers:
* **Tier 1 (Independent Catalogs):** `departments`, `users`, `producers`, `international_buyers`, `coffee_varieties`, `sensor_types`, `crop_nutrient_references` (F1).
* **Tier 2 (Regional & Spatial):** `municipalities`, `forest_reserves`.
* **Tier 3 (Core Entities):** `farms`, `farm_reserve_overlaps`, `farm_plots`.
* **Tier 4 (Operational & Hardware):** `iot_sensors`, `sensor_anomalies_log`, `soil_lab_analyses` (F6), `fertilizer_recommendations`, `harvest_deliveries`.
* **Tier 5 (Aggregations, Traceability & Alerts):** `export_batches`, `batch_farm_compositions`, `cupping_evaluations`, `buyer_batch_contracts`, `agronomic_alerts`, `agronomist_field_visits`.

---

## 3. Expected Database State (Before & After Execution)

### 3.1 State Before Execution
The script safely accepts any of the following initial states:
* **Empty Migrated Schema:** Fresh PostgreSQL database where Alembic/ORM migrations have created the tables, but all row counts are `0`.
* **Pre-Populated / Dirty State:** Database containing records from a previous seed run or partial manual tests.
  * *Without `--reset`:* Existing seed records are updated in-place via `ON CONFLICT DO UPDATE` without creating duplicates.
  * *With `--reset`:* All tables are wiped and sequences reset prior to fresh population.

### 3.2 State After Execution (Verifiable Row Counts)
After running the script once, twice, or $N$ times, the database must converge to the exact row counts defined below (supporting both `prod` full scale and `dev` lightweight scale per **Section 5.2**):

| Table / Metric | `prod` Mode (Full Volume) | `dev` Mode (Local Fast) | Verification / Business Rule |
| :--- | :--- | :--- | :--- |
| `farms` (Total) | `1,300` rows | `130` rows | Exact cooperative size (Section 1). |
| `farms` (`has_pilot_sensors = TRUE`) | `300` rows | `30` rows | Pilot farms equipped with IoT sensors (**F4**). |
| `iot_sensors` | `900` rows (300 × 3) | `90` rows (30 × 3) | 3 sensors per pilot farm (`SOIL_MOISTURE`, `TEMP`, `RAIN`). |
| `harvest_deliveries` | `~15,000` rows/year | `1,500` rows | Operational harvest deliveries (**F5**). |
| `international_buyers` | `40` rows | `10` rows | Active international buyers with isolated credentials (**F7**). |
| `crop_nutrient_references` | `~2,200` rows | `~2,200` rows | Static Kaggle reference dataset (**F1**). |
| `soil_lab_analyses` | `1,200` rows (100/mo) | `120` rows | Simulated lab reports including mixed units (**F6**). |
| **Injected Data Defects** | Configurable (default `5%`)| Configurable (default `5%`)| Inverted coords, stuck sensors, unlinked batches (Sec 5.3). |
| **Duplicate Records** | `0` duplicates | `0` duplicates | Verified by running the script twice (**CT-06**). |

---

## 4. Standard CLI Execution Commands

The seed module is exposed as a reproducible CLI entry point compatible with both local Docker Compose and AWS RDS environments:

```bash
# 1. Standard idempotent execution (Full production volume, safe re-run via UPSERT)
uv run python -m scripts.seed --mode prod --seed 42

# 2. Lightweight development execution (Fast local startup < 30 min for CT-01)
uv run python -m scripts.seed --mode dev --seed 42

# 3. Full cleanup and reset from scratch (TRUNCATE CASCADE + RESTART IDENTITY)
uv run python -m scripts.seed --mode prod --seed 42 --reset

# 4. Custom data quality defect injection rate (Section 5.3 testing)
uv run python -m scripts.seed --mode dev --seed 42 --defect-rate 0.10 --reset
