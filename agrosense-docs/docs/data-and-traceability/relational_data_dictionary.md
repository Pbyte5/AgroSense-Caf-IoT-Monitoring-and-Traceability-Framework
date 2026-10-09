# Relational Data Dictionary and Column Specification

This document defines the column-level technical specification for the relational database (**PostgreSQL 16+**) of **AgroSense Café**. It serves as the implementation blueprint for schema migrations (Alembic / SQLAlchemy), integrity constraints, and indexing.

---

## General Schema Conventions

- **Database Engine:** PostgreSQL 16+
- **UUID Extension:** `pgcrypto` (`gen_random_uuid()`) is required for distributed primary keys.
- **Time Zone:** All timestamps use `TIMESTAMPTZ` stored in UTC.
- **Naming:** Strict `snake_case` for table names, columns, indexes, and constraints.

---

## MODULE 1: Core & Farms

### 1.1 Table: `departments`

Geographic catalog of coffee-producing departments.

| Field Name        | SQL Data Type    | PK | FK | Nullability | Default               | Notes and Constraints (CHECK / Constraints)                         |
| :---------------- | :--------------- | :-: | :- | :----------: | :-------------------- | :------------------------------------------------------------------ |
| `department_id` | `SERIAL`       | ✅ | — | `NOT NULL` | `nextval()`         | Unique identifier of the department.                                |
| `dane_code`     | `VARCHAR(5)`   | — | — | `NOT NULL` | —                    | `UNIQUE`. Official administrative code (e.g. `'05'`, `'17'`). |
| `name`          | `VARCHAR(100)` | — | — | `NOT NULL` | —                    | `UNIQUE`. Official name of the department.                        |
| `created_at`    | `TIMESTAMPTZ`  | — | — | `NOT NULL` | `CURRENT_TIMESTAMP` | Record creation date.                                               |

> **Table notes:** Static, low-cardinality dimensional table; indexed by `dane_code`.

---

### 1.2 Table: `municipalities`

Catalog of coffee-growing municipalities associated with a department (Source F1).

| Field Name            | SQL Data Type    | PK | FK                                        | Nullability | Default               | Notes and Constraints (CHECK / Constraints)                                      |
| :-------------------- | :--------------- | :-: | :---------------------------------------- | :----------: | :-------------------- | :------------------------------------------------------------------------------- |
| `municipality_id`   | `SERIAL`       | ✅ | —                                        | `NOT NULL` | `nextval()`         | Unique identifier of the municipality.                                           |
| `department_id`     | `INTEGER`      | — | `REFERENCES departments(department_id)` | `NOT NULL` | —                    | `ON DELETE RESTRICT`.                                                          |
| `dane_code`         | `VARCHAR(10)`  | — | —                                        | `NOT NULL` | —                    | `UNIQUE`. Official municipality code.                                          |
| `name`              | `VARCHAR(120)` | — | —                                        | `NOT NULL` | —                    | Municipality name.                                                               |
| `altitude_avg_masl` | `INTEGER`      | — | —                                        |   `NULL`   | `NULL`              | `CHECK (altitude_avg_masl BETWEEN 400 AND 3000)`. Average altitude in m.a.s.l. |
| `created_at`        | `TIMESTAMPTZ`  | — | —                                        | `NOT NULL` | `CURRENT_TIMESTAMP` | Record date.                                                                     |

> **Table notes:** Composite index on `(department_id, name)`.

---

### 1.3 Table: `coffee_varieties`

Catalog of coffee varieties grown in the cooperative and their biological resistance to pests.

| Field Name                | SQL Data Type    | PK | FK | Nullability | Default       | Notes and Constraints (CHECK / Constraints)                                                         |
| :------------------------ | :--------------- | :-: | :- | :----------: | :------------ | :-------------------------------------------------------------------------------------------------- |
| `variety_id`            | `SERIAL`       | ✅ | — | `NOT NULL` | `nextval()` | Unique identifier of the variety.                                                                   |
| `name`                  | `VARCHAR(80)`  | — | — | `NOT NULL` | —            | `UNIQUE` (e.g. `'Castillo'`, `'Caturra'`, `'Geisha'`, `'Tabi'`).                          |
| `rust_resistance_level` | `VARCHAR(20)`  | — | — | `NOT NULL` | `'MEDIUM'`  | `CHECK (rust_resistance_level IN ('LOW', 'MEDIUM', 'HIGH'))`. Level of resistance to coffee rust. |
| `optimal_temp_min_c`    | `NUMERIC(4,1)` | — | — | `NOT NULL` | `17.0`      | `CHECK (optimal_temp_min_c >= 10.0)`. Ideal minimum temperature (°C).                            |
| `optimal_temp_max_c`    | `NUMERIC(4,1)` | — | — | `NOT NULL` | `24.0`      | `CHECK (optimal_temp_max_c <= 35.0)`. Ideal maximum temperature (°C).                            |

> **Table notes:** Used in the agronomic rules to weight a plot's vulnerability to rust alerts.

---

### 1.4 Table: `farms`

Master registry of the 1,300 farms affiliated with the cooperative (Source F1).

| Field Name               | SQL Data Type    | PK | FK                                             | Nullability | Default               | Notes and Constraints (CHECK / Constraints)                                       |
| :----------------------- | :--------------- | :-: | :--------------------------------------------- | :----------: | :-------------------- | :-------------------------------------------------------------------------------- |
| `farm_id`              | `UUID`         | ✅ | —                                             | `NOT NULL` | `gen_random_uuid()` | Universally unique identifier of the farm.                                        |
| `farm_code`            | `VARCHAR(20)`  | — | —                                             | `NOT NULL` | —                    | `UNIQUE`. Internal cooperative code (e.g. `'FIN-0042'`).                      |
| `municipality_id`      | `INTEGER`      | — | `REFERENCES municipalities(municipality_id)` | `NOT NULL` | —                    | Municipality where the farm is located.                                           |
| `name`                 | `VARCHAR(150)` | — | —                                             | `NOT NULL` | —                    | Farm name.                                                                        |
| `producer_name`        | `VARCHAR(150)` | — | —                                             | `NOT NULL` | —                    | Full name of the coffee grower who owns the farm.                                 |
| `latitude`             | `NUMERIC(9,6)` | — | —                                             | `NOT NULL` | —                    | `CHECK (latitude BETWEEN -4.23 AND 13.50)`. Geographic latitude coordinate.     |
| `longitude`            | `NUMERIC(9,6)` | — | —                                             | `NOT NULL` | —                    | `CHECK (longitude BETWEEN -81.73 AND -66.85)`. Geographic longitude coordinate. |
| `altitude_masl`        | `INTEGER`      | — | —                                             | `NOT NULL` | —                    | `CHECK (altitude_masl BETWEEN 800 AND 2600)`. Altitude in m.a.s.l.              |
| `total_area_ha`        | `NUMERIC(8,2)` | — | —                                             | `NOT NULL` | —                    | `CHECK (total_area_ha > 0)`. Total hectares of the property.                    |
| `is_pilot_sensor_farm` | `BOOLEAN`      | — | —                                             | `NOT NULL` | `FALSE`             | Indicates whether it belongs to the group of 300 pilot farms with IoT sensors.    |
| `is_active`            | `BOOLEAN`      | — | —                                             | `NOT NULL` | `TRUE`              | Active status of the farm in the cooperative.                                     |
| `created_at`           | `TIMESTAMPTZ`  | — | —                                             | `NOT NULL` | `CURRENT_TIMESTAMP` | Date registered in the system.                                                    |

> **Table notes:** Indexes on `farm_code`, `municipality_id`, and a spatial/composite index on `(latitude, longitude)` for satellite weather joins (NASA POWER / Open-Meteo).

---

### 1.5 Table: `farm_plots`

Productive subdivision (internal plots or sections) within each farm.

| Field Name              | SQL Data Type    | PK | FK                                          | Nullability | Default               | Notes and Constraints (CHECK / Constraints)                                |
| :---------------------- | :--------------- | :-: | :------------------------------------------ | :----------: | :-------------------- | :------------------------------------------------------------------------- |
| `plot_id`             | `UUID`         | ✅ | —                                          | `NOT NULL` | `gen_random_uuid()` | Unique identifier of the farm's internal plot.                             |
| `farm_id`             | `UUID`         | — | `REFERENCES farms(farm_id)`               | `NOT NULL` | —                    | `ON DELETE CASCADE`. Farm the plot belongs to.                           |
| `variety_id`          | `INTEGER`      | — | `REFERENCES coffee_varieties(variety_id)` | `NOT NULL` | —                    | Variety planted in the plot.                                               |
| `plot_number`         | `INTEGER`      | — | —                                          | `NOT NULL` | —                    | `CHECK (plot_number > 0)`. Sequential number within the farm.            |
| `cultivated_area_ha`  | `NUMERIC(7,2)` | — | —                                          | `NOT NULL` | —                    | `CHECK (cultivated_area_ha > 0)`. Cultivated area in hectares.           |
| `tree_density_per_ha` | `INTEGER`      | — | —                                          | `NOT NULL` | `5000`              | `CHECK (tree_density_per_ha BETWEEN 1000 AND 12000)`. Trees per hectare. |
| `planting_date`       | `DATE`         | — | —                                          |   `NULL`   | `NULL`              | Planting date or date of the last renewal by stumping (zoca).              |

> **Table notes:** `UNIQUE (farm_id, plot_number)` constraint to avoid duplicate plots within the same farm.

---

## MODULE 2: IoT & Telemetry

### 2.1 Table: `iot_sensors`

Inventory and status of the sensors installed on the 300 pilot farms (Source F4).

| Field Name           | SQL Data Type   | PK | FK                                 | Nullability | Default               | Notes and Constraints (CHECK / Constraints)                                               |
| :------------------- | :-------------- | :-: | :--------------------------------- | :----------: | :-------------------- | :---------------------------------------------------------------------------------------- |
| `sensor_id`        | `UUID`        | ✅ | —                                 | `NOT NULL` | `gen_random_uuid()` | Unique identifier of the IoT device.                                                      |
| `serial_number`    | `VARCHAR(50)` | — | —                                 | `NOT NULL` | —                    | `UNIQUE`. Manufacturer's physical serial number.                                        |
| `farm_id`          | `UUID`        | — | `REFERENCES farms(farm_id)`      | `NOT NULL` | —                    | Farm where the sensor is installed.                                                       |
| `plot_id`          | `UUID`        | — | `REFERENCES farm_plots(plot_id)` |   `NULL`   | `NULL`              | Specific plot being monitored.                                                            |
| `sensor_type`      | `VARCHAR(30)` | — | —                                 | `NOT NULL` | `'MULTI_AGRO'`      | `CHECK (sensor_type IN ('SOIL_MOISTURE', 'TEMPERATURE', 'PLUVIOMETER', 'MULTI_AGRO'))`. |
| `firmware_version` | `VARCHAR(20)` | — | —                                 | `NOT NULL` | `'v1.0.0'`          | Current firmware version of the node.                                                     |
| `status`           | `VARCHAR(20)` | — | —                                 | `NOT NULL` | `'ACTIVE'`          | `CHECK (status IN ('ACTIVE', 'OFFLINE', 'MAINTENANCE', 'RETIRED'))`.                    |
| `last_seen_at`     | `TIMESTAMPTZ` | — | —                                 |   `NULL`   | `NULL`              | Last cellular-network synchronization timestamp (ACK).                                    |
| `installed_at`     | `DATE`        | — | —                                 | `NOT NULL` | `CURRENT_DATE`      | Field installation date.                                                                  |

> **Table notes:** Supports RNF-01 by tracking `last_seen_at` to detect sensors disconnected for up to 7 days.

---

### 2.2 Table: `sensor_anomalies_log`

Audit log for readings that were discarded or flagged as anomalous during the Bronze-to-Silver transition.

| Field Name            | SQL Data Type   | PK | FK                                    | Nullability | Default               | Notes and Constraints (CHECK / Constraints)                                                           |
| :-------------------- | :-------------- | :-: | :------------------------------------ | :----------: | :-------------------- | :---------------------------------------------------------------------------------------------------- |
| `anomaly_id`        | `BIGSERIAL`   | ✅ | —                                    | `NOT NULL` | `nextval()`         | Sequential identifier of the anomalous event.                                                         |
| `sensor_id`         | `UUID`        | — | `REFERENCES iot_sensors(sensor_id)` | `NOT NULL` | —                    | Sensor that originated the faulty reading.                                                            |
| `reading_timestamp` | `TIMESTAMPTZ` | — | —                                    | `NOT NULL` | —                    | Original timestamp of the reading in the field.                                                       |
| `received_at`       | `TIMESTAMPTZ` | — | —                                    | `NOT NULL` | `CURRENT_TIMESTAMP` | Moment the IoT queue received the delayed block.                                                      |
| `anomaly_type`      | `VARCHAR(40)` | — | —                                    | `NOT NULL` | —                    | `CHECK (anomaly_type IN ('OUT_OF_RANGE', 'DUPLICATE_BLOCK', 'STALE_OVER_7_DAYS', 'NULL_PAYLOAD'))`. |
| `raw_payload`       | `JSONB`       | — | —                                    | `NOT NULL` | —                    | Raw reading received, for technical diagnosis.                                                        |

> **Table notes:** Clean time series live in the Data Lake (Parquet partitioned by day); this relational table only records data quality failures for hardware maintenance.

---

## MODULE 3: Soils & Nutrition

### 3.1 Table: `soil_lab_analyses`

Physicochemical laboratory results per plot (Source F5).

| Field Name             | SQL Data Type    | PK | FK                                 | Nullability | Default               | Notes and Constraints (CHECK / Constraints)                                           |
| :--------------------- | :--------------- | :-: | :--------------------------------- | :----------: | :-------------------- | :------------------------------------------------------------------------------------ |
| `analysis_id`        | `UUID`         | ✅ | —                                 | `NOT NULL` | `gen_random_uuid()` | Unique identifier of the soil analysis.                                               |
| `plot_id`            | `UUID`         | — | `REFERENCES farm_plots(plot_id)` | `NOT NULL` | —                    | Plot evaluated.                                                                       |
| `sample_date`        | `DATE`         | — | —                                 | `NOT NULL` | —                    | Date the sample was taken in the field.                                               |
| `ph_level`           | `NUMERIC(4,2)` | — | —                                 | `NOT NULL` | —                    | `CHECK (ph_level BETWEEN 3.00 AND 9.50)`. Soil acidity.                             |
| `organic_matter_pct` | `NUMERIC(5,2)` | — | —                                 | `NOT NULL` | —                    | `CHECK (organic_matter_pct BETWEEN 0.00 AND 100.00)`. Percentage of organic matter. |
| `nitrogen_ppm`       | `NUMERIC(7,2)` | — | —                                 | `NOT NULL` | —                    | `CHECK (nitrogen_ppm >= 0)`. Available nitrogen (ppm).                              |
| `phosphorus_ppm`     | `NUMERIC(7,2)` | — | —                                 | `NOT NULL` | —                    | `CHECK (phosphorus_ppm >= 0)`. Available phosphorus (ppm).                          |
| `potassium_cmol_kg`  | `NUMERIC(6,2)` | — | —                                 | `NOT NULL` | —                    | `CHECK (potassium_cmol_kg >= 0)`. Exchangeable potassium (cmol/kg).                 |
| `soil_texture`       | `VARCHAR(30)`  | — | —                                 | `NOT NULL` | —                    | `CHECK (soil_texture IN ('SANDY', 'LOAM', 'CLAY_LOAM', 'CLAY', 'SILTY'))`.          |

> **Table notes:** Index on `(plot_id, sample_date DESC)` to quickly retrieve the current analysis for each plot.

---

### 3.2 Table: `crop_nutrient_references`

Ideal agronomic nutrition parameters by variety and phenological stage, to avoid generic fertilization.

| Field Name               | SQL Data Type    | PK | FK                                          | Nullability | Default       | Notes and Constraints (CHECK / Constraints)                                               |
| :----------------------- | :--------------- | :-: | :------------------------------------------ | :----------: | :------------ | :---------------------------------------------------------------------------------------- |
| `reference_id`         | `SERIAL`       | ✅ | —                                          | `NOT NULL` | `nextval()` | Unique identifier of the nutrition rule.                                                  |
| `variety_id`           | `INTEGER`      | — | `REFERENCES coffee_varieties(variety_id)` | `NOT NULL` | —            | Applicable coffee variety.                                                                |
| `growth_stage`         | `VARCHAR(30)`  | — | —                                          | `NOT NULL` | —            | `CHECK (growth_stage IN ('VEGETATIVE', 'FLOWERING', 'GRAIN_FILLING', 'POST_HARVEST'))`. |
| `target_ph_min`        | `NUMERIC(4,2)` | — | —                                          | `NOT NULL` | `5.00`      | `CHECK (target_ph_min >= 4.00)`. Minimum recommended pH.                                |
| `target_ph_max`        | `NUMERIC(4,2)` | — | —                                          | `NOT NULL` | `5.80`      | `CHECK (target_ph_max <= 7.00)`. Maximum recommended pH.                                |
| `req_nitrogen_kg_ha`   | `NUMERIC(6,2)` | — | —                                          | `NOT NULL` | —            | `CHECK (req_nitrogen_kg_ha >= 0)`. N requirement per hectare.                           |
| `req_phosphorus_kg_ha` | `NUMERIC(6,2)` | — | —                                          | `NOT NULL` | —            | `CHECK (req_phosphorus_kg_ha >= 0)`. P requirement per hectare.                         |
| `req_potassium_kg_ha`  | `NUMERIC(6,2)` | — | —                                          | `NOT NULL` | —            | `CHECK (req_potassium_kg_ha >= 0)`. K requirement per hectare.                          |

> **Table notes:** `UNIQUE (variety_id, growth_stage)` constraint.

---

### 3.3 Table: `fertilizer_recommendations`

Fertilization plans calculated per farm/plot to reach the goal of a 20% reduction in chemical inputs.

| Field Name               | SQL Data Type    | PK | FK                                            | Nullability | Default               | Notes and Constraints (CHECK / Constraints)                                                               |
| :----------------------- | :--------------- | :-: | :-------------------------------------------- | :----------: | :-------------------- | :-------------------------------------------------------------------------------------------------------- |
| `recommendation_id`    | `UUID`         | ✅ | —                                            | `NOT NULL` | `gen_random_uuid()` | Unique identifier of the recommendation.                                                                  |
| `plot_id`              | `UUID`         | — | `REFERENCES farm_plots(plot_id)`            | `NOT NULL` | —                    | Target plot.                                                                                              |
| `analysis_id`          | `UUID`         | — | `REFERENCES soil_lab_analyses(analysis_id)` | `NOT NULL` | —                    | Soil analysis that supports the calculation.                                                              |
| `generated_at`         | `TIMESTAMPTZ`  | — | —                                            | `NOT NULL` | `CURRENT_TIMESTAMP` | Date generated by the rules engine (Gold).                                                                |
| `recommended_n_kg_ha`  | `NUMERIC(6,2)` | — | —                                            | `NOT NULL` | —                    | `CHECK (recommended_n_kg_ha >= 0)`. Adjusted Nitrogen dose.                                             |
| `recommended_p_kg_ha`  | `NUMERIC(6,2)` | — | —                                            | `NOT NULL` | —                    | `CHECK (recommended_p_kg_ha >= 0)`. Adjusted Phosphorus dose.                                           |
| `recommended_k_kg_ha`  | `NUMERIC(6,2)` | — | —                                            | `NOT NULL` | —                    | `CHECK (recommended_k_kg_ha >= 0)`. Adjusted Potassium dose.                                            |
| `lime_amendment_kg_ha` | `NUMERIC(7,2)` | — | —                                            | `NOT NULL` | `0.00`              | `CHECK (lime_amendment_kg_ha >= 0)`. Lime required if the pH is too acidic.                             |
| `estimated_saving_pct` | `NUMERIC(5,2)` | — | —                                            | `NOT NULL` | `0.00`              | `CHECK (estimated_saving_pct BETWEEN -100.00 AND 100.00)`. Savings versus the traditional generic dose. |
| `status`               | `VARCHAR(20)`  | — | —                                            | `NOT NULL` | `'PENDING'`         | `CHECK (status IN ('PENDING', 'APPLIED', 'EXPIRED'))`.                                                  |

> **Table notes:** Feeds the per-plot sustainability indicators and the agronomic management dashboard.

---

## MODULE 4: Alerts & Visits

### 4.1 Table: `agronomic_alerts`

Early warnings generated at least 5 days in advance, before 05:00 a.m. (RNF-02).

| Field Name   | SQL Data Type | PK | FK                            | Nullability | Default               | Notes and Constraints (CHECK / Constraints) |
| :----------- | :------------ | :-: | :---------------------------- | :----------: | :-------------------- | :------------------------------------------ |
| `alert_id` | `UUID`      | ✅ | —                            | `NOT NULL` | `gen_random_uuid()` | Unique identifier of the alert.             |
| `farm_id`  | `UUID`      | — | `REFERENCES farms(farm_id)` | `NOT NULL` | —                    |                                             |
