# 🛠️ AgroSense Café — Dataset & Database Structure Specification

In this document, we define the complete schema design, relational tables (3NF), Data Lake structures (Medallion Architecture), and Analytical Star Schema required for the **AgroSense Café** platform[cite: 1, 2].

---

## PART 1: Operational Relational Database (PostgreSQL — 3NF)
This layer handles transactional operations, master data, traceability, and low-latency API queries ($p95 \le 500\text{ ms}$, **RNF-03**).

### Module 1.1: Geography & Forest Conservation (F5, RN-09)

#### 1. Table: `departments`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `department_id` | `INT` | `PK` | Unique identifier for the department/state. |
| `dane_code` | `VARCHAR(10)` | `UNIQUE, NOT NULL` | Official geographic code. |
| `name` | `VARCHAR(100)` | `NOT NULL` | Department name (e.g., Antioquia, Huila, Caldas). |

#### 2. Table: `municipalities`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `municipality_id` | `INT` | `PK` | Unique identifier for the municipality. |
| `department_id` | `INT` | `FK -> departments` | Parent department reference. |
| `dane_code` | `VARCHAR(10)` | `UNIQUE, NOT NULL` | Official municipality code. |
| `name` | `VARCHAR(100)` | `NOT NULL` | Used for regional alert aggregation in Power BI (Section 13). |

#### 3. Table: `forest_reserves`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `reserve_id` | `UUID` | `PK` | Unique identifier for the protected reserve (**RN-09**). |
| `municipality_id` | `INT` | `FK -> municipalities`| Municipality where the reserve is located. |
| `name` | `VARCHAR(150)` | `NOT NULL` | Official name of the protected forest area. |
| `polygon_geojson` | `JSONB` | `NOT NULL` | Spatial boundary used to detect deforestation/overlap. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | Record creation timestamp. |

#### 4. Table: `farm_reserve_overlaps`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `overlap_id` | `UUID` | `PK` | Unique identifier for the spatial intersection record. |
| `farm_id` | `UUID` | `FK -> farms` | Farm being evaluated. |
| `reserve_id` | `UUID` | `FK -> forest_reserves`| Reserve overlapping with the farm. |
| `overlap_area_ha` | `DECIMAL(10,2)` | `NOT NULL` | Intersected area in hectares (> 0 blocks certification in **CA-08**). |
| `verified_at` | `TIMESTAMPTZ` | `NOT NULL` | Timestamp of the spatial validation check. |

---

### Module 1.2: Actors, Producers & Security (Section 4, RNF-06, RN-11)

#### 5. Table: `users`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `user_id` | `UUID` | `PK` | Unique internal user ID. |
| `full_name` | `VARCHAR(150)` | `NOT NULL` | Name of the staff member. |
| `email` | `VARCHAR(150)` | `UNIQUE, NOT NULL` | Institutional login email. |
| `password_hash` | `VARCHAR(255)` | `NOT NULL` | Hashed credential (Never stored in plain text — **CT-02**). |
| `role` | `VARCHAR(50)` | `NOT NULL` | `AGRONOMIST`, `QUALITY_CHIEF`, `SUSTAINABILITY_COMMITTEE`, `ADMIN`. |
| `is_active` | `BOOLEAN` | `DEFAULT TRUE` | Account status flag. |

#### 6. Table: `producers`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `producer_id` | `UUID` | `PK` | Unique ID for the coffee grower/owner. |
| `document_number` | `VARCHAR(30)` | `UNIQUE, NOT NULL` | National ID / Tax ID of the producer. |
| `full_name` | `VARCHAR(150)` | `NOT NULL` | Producer's full name. |
| `phone_number` | `VARCHAR(30)` | `NULL` | Contact number for receiving simple farm alerts. |
| `cooperative_join_date`| `DATE` | `NOT NULL` | Date of affiliation with AgroSense Cooperative. |

#### 7. Table: `international_buyers`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `buyer_id` | `UUID` | `PK` | Unique ID for the international buyer (~40 buyers — **F7**). |
| `company_name` | `VARCHAR(150)` | `NOT NULL` | Legal name of the importing company. |
| `country` | `VARCHAR(80)` | `NOT NULL` | Destination country. |
| `client_id` | `VARCHAR(80)` | `UNIQUE, NOT NULL` | Public identifier for API authentication (**RNF-06**). |
| `api_key_hash` | `VARCHAR(255)` | `NOT NULL` | Secret hash managed via Secrets Manager for data isolation (**RN-11**). |
| `is_active` | `BOOLEAN` | `DEFAULT TRUE` | Access control flag. |

#### 8. Table: `buyer_api_audit_logs`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `audit_id` | `BIGSERIAL` | `PK` | Unique log entry ID. |
| `buyer_id` | `UUID` | `FK -> international_buyers` | Buyer performing the request. |
| `batch_id` | `UUID` | `FK -> export_batches` | Requested export batch. |
| `http_status_code` | `INT` | `NOT NULL` | `200` (OK) or `403` (Forbidden — proves **CA-09**). |
| `latency_ms` | `DECIMAL(8,2)` | `NOT NULL` | Execution time in ms (Monitors $p95 \le 500\text{ ms}$ — **RNF-03**). |
| `requested_at` | `TIMESTAMPTZ` | `NOT NULL` | Timestamp of the API request. |

---

### Module 1.3: Farms, Varieties & Cultivation Plots (F5)

#### 9. Table: `coffee_varieties`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `variety_id` | `INT` | `PK` | Unique ID for the coffee variety. |
| `name` | `VARCHAR(80)` | `UNIQUE, NOT NULL` | e.g., Castillo, Caturra, Bourbon, Tabi, Geisha. |
| `rust_susceptibility` | `VARCHAR(30)` | `NOT NULL` | `HIGH`, `MEDIUM`, `LOW` (Contextualizes coffee rust risk). |

#### 10. Table: `farms`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `farm_id` | `UUID` | `PK` | Unique ID for each of the 1,300 farms. |
| `farm_code` | `VARCHAR(30)` | `UNIQUE, NOT NULL` | Human-readable business code (e.g., `FIN-0001`). |
| `producer_id` | `UUID` | `FK -> producers` | Owner of the farm. |
| `municipality_id` | `INT` | `FK -> municipalities`| Geographic location of the farm. |
| `name` | `VARCHAR(150)` | `NOT NULL` | Farm name. |
| `latitude` | `DECIMAL(9,6)` | `NOT NULL` | Latitude for NASA POWER (F2) & Open-Meteo (F3) queries. |
| `longitude` | `DECIMAL(9,6)` | `NOT NULL` | Longitude (Validated against inverted lat/lon defects — Sec 5.3). |
| `altitude_msl` | `INT` | `NOT NULL` | Altitude in meters above sea level. |
| `total_area_ha` | `DECIMAL(10,2)` | `NOT NULL` | Total property surface in hectares. |
| `cultivated_area_ha` | `DECIMAL(10,2)` | `NOT NULL` | Cultivated coffee area (Tie-breaker in visit priority — **RN-06**). |
| `polygon_geojson` | `JSONB` | `NOT NULL` | Full farm perimeter polygon. |
| `has_pilot_sensors` | `BOOLEAN` | `DEFAULT FALSE` | `TRUE` for the 300 pilot farms with IoT hardware. |
| `water_usage_m3_ton` | `DECIMAL(10,2)` | `NOT NULL` | Water consumption rate per ton of coffee (**RN-10**). |
| `overlaps_reserve` | `BOOLEAN` | `DEFAULT FALSE` | Denormalized flag updated from `farm_reserve_overlaps` (**RN-09**). |
| `has_valid_coords` | `BOOLEAN` | `DEFAULT TRUE` | `FALSE` if seed injected inverted or out-of-country coordinates. |

#### 11. Table: `farm_plots` (Blocks)
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `plot_id` | `UUID` | `PK` | Unique identifier for the cultivation block within a farm. |
| `farm_id` | `UUID` | `FK -> farms` | Parent farm reference. |
| `variety_id` | `INT` | `FK -> coffee_varieties`| Planted coffee variety. |
| `plot_name` | `VARCHAR(80)` | `NOT NULL` | Internal block name/number (e.g., `Lote Norte 1`). |
| `plot_area_ha` | `DECIMAL(10,2)` | `NOT NULL` | Area of the specific plot in hectares. |
| `crop_age_years` | `INT` | `NOT NULL` | Age of the coffee trees in years. |
| `polygon_geojson` | `JSONB` | `NULL` | Specific polygon of the cultivation block. |

---

### Module 1.4: IoT Sensors & Telemetry Health (F4, RN-01, RN-02, RF-08)

#### 12. Table: `sensor_types`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `sensor_type_id` | `INT` | `PK` | Unique ID for the sensor category. |
| `type_code` | `VARCHAR(40)` | `UNIQUE, NOT NULL` | `SOIL_MOISTURE`, `TEMPERATURE`, `PLUVIOMETRY`. |
| `canonical_unit` | `VARCHAR(20)` | `NOT NULL` | `%`, `CELSIUS`, `MM`. |
| `expected_interval_min`| `INT` | `DEFAULT 10` | Ideal sampling interval (10 minutes — **F4**). |

#### 13. Table: `iot_sensors`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `sensor_id` | `UUID` | `PK` | Unique ID for each of the 900 sensors (300 farms × 3). |
| `serial_number` | `VARCHAR(60)` | `UNIQUE, NOT NULL` | Hardware serial code. |
| `farm_id` | `UUID` | `FK -> farms` | Farm where the sensor is installed. |
| `plot_id` | `UUID` | `FK -> farm_plots` | Specific plot monitored. |
| `sensor_type_id` | `INT` | `FK -> sensor_types` | Type of measurement captured. |
| `health_status` | `VARCHAR(30)` | `NOT NULL` | `ACTIVE`, `DEFECTIVE_STUCK` (**RN-02**), `DISCONNECTED`, `LOW_BATTERY`. |
| `clock_drift_seconds` | `INT` | `DEFAULT 0` | Known device clock offset corrected during ingestion (**RN-01**). |
| `battery_level_pct` | `DECIMAL(5,2)` | `NOT NULL` | Latest reported battery percentage. |
| `last_transmission_at`| `TIMESTAMPTZ` | `NULL` | Timestamp of the last received block. |

#### 14. Table: `sensor_anomalies_log`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `anomaly_id` | `UUID` | `PK` | Unique ID for the detected hardware issue. |
| `sensor_id` | `UUID` | `FK -> iot_sensors` | Affected sensor. |
| `anomaly_type` | `VARCHAR(50)` | `NOT NULL` | `STUCK_24H` (<0.5% variation — **RN-02**), `DRIFT_EXCEEDED`, `DEAD_BATTERY`. |
| `variation_pct_24h` | `DECIMAL(6,4)` | `NULL` | Recorded variation over 24h proving **CA-02**. |
| `detected_at` | `TIMESTAMPTZ` | `NOT NULL` | When the Spark job flagged the sensor. |
| `is_resolved` | `BOOLEAN` | `DEFAULT FALSE` | Resolution status. |

---

### Module 1.5: Soil Analysis & Fertilization Engine (F1, F6, RN-07, RF-04)

#### 15. Table: `crop_nutrient_references` (Source F1 — Kaggle Dataset)
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `reference_id` | `SERIAL` | `PK` | Unique ID from the ~2,200 Kaggle rows or aggregated thresholds. |
| `crop_label` | `VARCHAR(50)` | `NOT NULL` | Crop name (Filtered primarily for `coffee`). |
| `n_min_mg_kg` | `DECIMAL(10,2)` | `NOT NULL` | Minimum Nitrogen reference threshold. |
| `n_max_mg_kg` | `DECIMAL(10,2)` | `NOT NULL` | Maximum Nitrogen reference threshold. |
| `p_min_mg_kg` | `DECIMAL(10,2)` | `NOT NULL` | Minimum Phosphorus reference threshold. |
| `p_max_mg_kg` | `DECIMAL(10,2)` | `NOT NULL` | Maximum Phosphorus reference threshold. |
| `k_min_mg_kg` | `DECIMAL(10,2)` | `NOT NULL` | Minimum Potassium reference threshold. |
| `k_max_mg_kg` | `DECIMAL(10,2)` | `NOT NULL` | Maximum Potassium reference threshold. |
| `ph_min` | `DECIMAL(4,2)` | `NOT NULL` | Minimum optimal soil pH. |
| `ph_max` | `DECIMAL(4,2)` | `NOT NULL` | Maximum optimal soil pH. |

#### 16. Table: `soil_lab_analyses` (Source F6 — Monthly Lab Reports)
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `analysis_id` | `UUID` | `PK` | Unique ID for the laboratory soil test (~100/month). |
| `farm_id` | `UUID` | `FK -> farms` | Analyzed farm. |
| `plot_id` | `UUID` | `FK -> farm_plots` | Analyzed plot (Optional). |
| `sample_date` | `DATE` | `NOT NULL` | Date the soil sample was taken. |
| `raw_unit_reported` | `VARCHAR(20)` | `NOT NULL` | Original lab unit (`ppm`, `mg/kg`, `%`, `g/kg` — Section 5.3). |
| `nitrogen_mg_kg` | `DECIMAL(10,2)` | `NOT NULL` | Standardized Nitrogen value in `mg/kg` (**CA-06**). |
| `phosphorus_mg_kg` | `DECIMAL(10,2)` | `NOT NULL` | Standardized Phosphorus value in `mg/kg` (**CA-06**). |
| `potassium_mg_kg` | `DECIMAL(10,2)` | `NOT NULL` | Standardized Potassium value in `mg/kg` (**CA-06**). |
| `ph_value` | `DECIMAL(4,2)` | `NOT NULL` | Measured soil pH. |

#### 17. Table: `fertilizer_recommendations`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `recommendation_id` | `UUID` | `PK` | Unique ID for the generated recommendation (**RN-07**). |
| `analysis_id` | `UUID` | `FK -> soil_lab_analyses`| Source soil analysis. |
| `farm_id` | `UUID` | `FK -> farms` | Target farm. |
| `n_evaluation` | `VARCHAR(20)` | `NOT NULL` | `DEFICIENT`, `OPTIMAL`, `EXCESS_WARNING`. |
| `p_evaluation` | `VARCHAR(20)` | `NOT NULL` | `DEFICIENT`, `OPTIMAL`, `EXCESS_WARNING`. |
| `k_evaluation` | `VARCHAR(20)` | `NOT NULL` | `DEFICIENT`, `OPTIMAL`, `EXCESS_WARNING`. |
| `ph_evaluation` | `VARCHAR(20)` | `NOT NULL` | `ACIDIC`, `OPTIMAL`, `ALKALINE`. |
| `apply_fertilizer` | `BOOLEAN` | `NOT NULL` | `FALSE` if nutrients exceed range (Issues "Do Not Apply" warning). |
| `recommended_n_kg_ha` | `DECIMAL(8,2)` | `NOT NULL` | Tailored Nitrogen dose in kg/ha. |
| `recommended_p_kg_ha` | `DECIMAL(8,2)` | `NOT NULL` | Tailored Phosphorus dose in kg/ha. |
| `recommended_k_kg_ha` | `DECIMAL(8,2)` | `NOT NULL` | Tailored Potassium dose in kg/ha. |
| `fertilizer_saved_pct`| `DECIMAL(5,2)` | `NOT NULL` | Estimated % saved vs generic baseline (Target: 20% — Sec 3). |
| `generated_at` | `TIMESTAMPTZ` | `NOT NULL` | Calculation timestamp. |

---

### Module 1.6: Harvests, Export Batches & Traceability (F5, RN-08, RN-10, RF-05)

#### 18. Table: `harvest_deliveries`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `delivery_id` | `UUID` | `PK` | Unique ID for each coffee delivery (~15,000/year). |
| `farm_id` | `UUID` | `FK -> farms, NULLABLE` | Origin farm (`NULL` allowed in dirty data to test **CA-07**). |
| `plot_id` | `UUID` | `FK -> farm_plots, NULL`| Origin plot. |
| `delivery_date` | `DATE` | `NOT NULL` | Date coffee was received at the cooperative. |
| `delivered_weight_kg` | `DECIMAL(10,2)` | `NOT NULL` | Kilograms of parchment coffee delivered. |
| `grain_moisture_pct` | `DECIMAL(5,2)` | `NOT NULL` | Moisture percentage at reception. |

#### 19. Table: `export_batches`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `batch_id` | `UUID` | `PK` | Unique ID for the export lot. |
| `batch_code` | `VARCHAR(40)` | `UNIQUE, NOT NULL` | Export lot code (e.g., `EXP-2026-0042`). |
| `created_date` | `DATE` | `NOT NULL` | Date the batch was consolidated. |
| `total_weight_kg` | `DECIMAL(12,2)` | `NOT NULL` | Total weight of the batch in kilograms. |
| `traced_weight_kg` | `DECIMAL(12,2)` | `NOT NULL` | Sum of kilograms with a valid `farm_id`. |
| `is_exportable` | `BOOLEAN` | `DEFAULT FALSE` | `TRUE` only if `traced_weight_kg == total_weight_kg` (**RN-08**, **CA-07**). |
| `is_certified` | `BOOLEAN` | `DEFAULT FALSE` | `FALSE` if any contributing farm overlaps a forest reserve (**RN-09**). |
| `weighted_water_m3_ton`| `DECIMAL(10,2)` | `NOT NULL` | Weighted average water usage by contributed kilos (**RN-10**). |
| `avg_fertilizer_red_pct`| `DECIMAL(5,2)` | `NOT NULL` | Sustainability indicator for fertilizer reduction (**RF-07**). |

#### 20. Table: `batch_farm_compositions`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `composition_id` | `UUID` | `PK` | Unique bridge record ID. |
| `batch_id` | `UUID` | `FK -> export_batches` | Target export batch. |
| `delivery_id` | `UUID` | `FK -> harvest_deliveries`| Source harvest delivery. |
| `farm_id` | `UUID` | `FK -> farms, NULLABLE` | Contributing farm (`NULL` triggers non-exportable status). |
| `contributed_kg` | `DECIMAL(10,2)` | `NOT NULL` | Kilograms contributed from this delivery to the batch. |
| `share_percentage` | `DECIMAL(6,3)` | `NOT NULL` | Percentage of total batch (Must be listed even if $< 5\%$ — **RN-08**). |

#### 21. Table: `cupping_evaluations`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `cupping_id` | `UUID` | `PK` | Unique ID for the quality cupping session. |
| `batch_id` | `UUID` | `FK -> export_batches` | Evaluated export batch. |
| `quality_chief_id` | `UUID` | `FK -> users` | Quality chief who performed the cupping. |
| `cupping_date` | `DATE` | `NOT NULL` | Date of sensory evaluation. |
| `sca_total_score` | `DECIMAL(5,2)` | `NOT NULL` | Specialty Coffee Association score (e.g., `85.50`). |
| `acidity_score` | `DECIMAL(4,2)` | `NOT NULL` | Sensory acidity rating. |
| `body_score` | `DECIMAL(4,2)` | `NOT NULL` | Sensory body rating. |
| `sensory_notes` | `TEXT` | `NOT NULL` | Tasting notes (e.g., chocolate, citrus, panela). |

#### 22. Table: `buyer_batch_contracts`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `contract_id` | `UUID` | `PK` | Unique sales contract ID. |
| `batch_id` | `UUID` | `FK -> export_batches` | Purchased coffee batch. |
| `buyer_id` | `UUID` | `FK -> international_buyers`| Buyer who owns the contract (Enforces **RN-11** & **CA-09**). |
| `purchase_date` | `DATE` | `NOT NULL` | Date of purchase. |
| `shipping_container_id`| `VARCHAR(40)` | `NOT NULL` | Maritime container code. |
| `destination_port` | `VARCHAR(100)` | `NOT NULL` | International destination port. |

---

### Module 1.7: Agronomic Alerts & Field Visits (RN-03 to RN-06, RNF-02)

#### 23. Table: `agronomic_alerts`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `alert_id` | `UUID` | `PK` | Unique ID for the generated alert. |
| `farm_id` | `UUID` | `FK -> farms` | Affected farm. |
| `alert_type` | `VARCHAR(30)` | `NOT NULL` | `COFFEE_RUST` (**RN-03**), `WATER_DEFICIT` (**RN-04**), `EXTREME_RAIN` (**RN-05**). |
| `weight_multiplier` | `INT` | `NOT NULL` | `3` for Rust, `2` for Water Deficit, `1` for Extreme Rain (**RN-06**). |
| `data_source_used` | `VARCHAR(30)` | `NOT NULL` | `IOT_SENSOR` or `SATELLITE_FALLBACK` (If sensor stuck/missing — **RN-03**). |
| `forecast_days_ahead` | `INT` | `NOT NULL` | Anticipation window ($\ge 5\text{ days}$ — Section 3). |
| `evidence_summary` | `JSONB` | `NOT NULL` | Metrics that triggered the rule (e.g., 4 days HR > 85%, T = 23°C). |
| `alert_status` | `VARCHAR(20)` | `NOT NULL` | `ACTIVE`, `ATTENDED`, `EXPIRED`. |
| `generated_at` | `TIMESTAMPTZ` | `NOT NULL` | Must be generated before `05:00 AM` daily (**RNF-02**). |

#### 24. Table: `agronomist_field_visits`
| Column | Type | Constraints | Description / Business Rule |
| :--- | :--- | :--- | :--- |
| `visit_id` | `UUID` | `PK` | Unique ID for the prioritized field visit. |
| `farm_id` | `UUID` | `FK -> farms` | Farm prioritized for visit. |
| `agronomist_id` | `UUID` | `FK -> users, NULLABLE` | Assigned field agronomist. |
| `calculation_date` | `DATE` | `NOT NULL` | Date the daily route was calculated. |
| `rust_alerts_count` | `INT` | `DEFAULT 0` | Active coffee rust alerts for this farm. |
| `deficit_alerts_count`| `INT` | `DEFAULT 0` | Active water deficit alerts for this farm. |
| `rain_alerts_count` | `INT` | `DEFAULT 0` | Active extreme rain alerts for this farm. |
| `priority_score` | `INT` | `NOT NULL` | Formula: $3(\text{Rust}) + 2(\text{Deficit}) + 1(\text{Rain})$ (**RN-06**, **CA-05**). |
| `tie_breaker_area_ha` | `DECIMAL(10,2)` | `NOT NULL` | Copy of `cultivated_area_ha` used to resolve score ties (**RN-06**). |
| `visit_status` | `VARCHAR(30)` | `NOT NULL` | `SCHEDULED`, `COMPLETED`, `UNATTENDED`. |
| `visit_outcome` | `VARCHAR(50)` | `NULL` | `CONTROLLED`, `PARTIAL_LOSS`, `FALSE_POSITIVE` (Power BI Q2 & Q6). |
| `visited_at` | `TIMESTAMPTZ` | `NULL` | Actual timestamp of the field visit. |

---

## PART 2: S3 Data Lake Schemas (Medallion Architecture — Bronze & Silver)
These datasets reside in Amazon S3 partitioned by date (`year=YYYY/month=MM/day=DD`) to allow incremental reprocessing of delayed 7-day IoT blocks (**RNF-01**) without recalculating the entire lake.

### Module 2.1: Bronze Layer (Raw Immutable Ingestion — JSON / CSV)

#### 25. Dataset: `s3://.../bronze/iot_telemetry/` (Source F4 — JSON via RabbitMQ & Lambda)
* **Columns:** `message_id` (STRING), `batch_upload_id` (STRING), `sensor_id` (STRING), `farm_id` (STRING), `device_timestamp_raw` (STRING), `server_ingestion_ts` (TIMESTAMP), `sensor_type` (STRING), `raw_value` (DOUBLE), `raw_unit` (STRING), `battery_pct` (DOUBLE).

#### 26. Dataset: `s3://.../bronze/nasa_power_daily/` (Source F2 — Daily Satellite JSON/CSV)
* **Columns:** `farm_id` (STRING), `latitude` (DOUBLE), `longitude` (DOUBLE), `observation_date` (DATE), `t2m_mean_celsius` (DOUBLE), `rh2m_pct` (DOUBLE), `prectotcorr_mm` (DOUBLE), `allsky_sfc_sw_dwn` (DOUBLE), `ingested_at` (TIMESTAMP).

#### 27. Dataset: `s3://.../bronze/open_meteo_forecast/` (Source F3 — Hourly 7-Day Forecast JSON)
* **Columns:** `farm_id` (STRING), `forecast_run_ts` (TIMESTAMP), `target_hour_ts` (TIMESTAMP), `temp_2m_celsius` (DOUBLE), `relative_humidity_pct` (DOUBLE), `precipitation_mm` (DOUBLE).

#### 28. Dataset: `s3://.../bronze/soil_lab_reports/` (Source F6 — Raw Monthly Lab CSV)
* **Columns:** `report_file_name` (STRING), `farm_code` (STRING), `sample_date_str` (STRING), `n_raw_value` (DOUBLE), `p_raw_value` (DOUBLE), `k_raw_value` (DOUBLE), `reported_unit` (STRING), `ph_raw` (DOUBLE).

#### 29. Dataset: `s3://.../bronze/kaggle_crop_reference/` (Source F1 — Static CSV)
* **Columns:** `N` (DOUBLE), `P` (DOUBLE), `K` (DOUBLE), `temperature` (DOUBLE), `humidity` (DOUBLE), `ph` (DOUBLE), `rainfall` (DOUBLE), `label` (STRING).

---

### Module 2.2: Silver Layer (Cleaned, Validated & Standardized — Apache Parquet)

#### 30. Dataset: `s3://.../silver/iot_readings_validated/`
* **Transformations Applied:** Sorted by device timestamp, corrected device clock drift, validated within $\pm 15\text{ min}$ sampling window (**RN-01**), deduplicated delayed 3-to-7-day blocks (**CA-01**), and flagged stuck sensors with $<0.5\%$ variation over 24h (**RN-02**).
* **Columns:** `reading_hash_id` (STRING - PK), `sensor_id` (STRING), `farm_id` (STRING), `sensor_type` (STRING), `corrected_timestamp` (TIMESTAMP), `expected_slot_ts` (TIMESTAMP), `deviation_minutes` (DOUBLE), `is_within_15m_window` (BOOLEAN), `is_sensor_stuck_24h` (BOOLEAN), `is_valid_for_alerts` (BOOLEAN), `standardized_value` (DOUBLE), `canonical_unit` (STRING), `partition_date` (DATE).

#### 31. Dataset: `s3://.../silver/agroclimatic_daily_features/`
* **Transformations Applied:** Joins valid IoT sensor readings with NASA POWER satellite fallback (**RN-03**) and aggregates Open-Meteo 5-day ahead rain forecasts (**RN-04**).
* **Columns:** `farm_id` (STRING), `observation_date` (DATE), `high_humidity_hours_gt85` (INT), `daily_mean_temp_c` (DOUBLE), `soil_moisture_mean_pct` (DOUBLE), `precip_accum_72h_mm` (DOUBLE), `forecast_rain_next_5d_mm` (DOUBLE), `consecutive_rust_days` (INT), `consecutive_dry_soil_days` (INT), `primary_source_used` (STRING).

#### 32. Dataset: `s3://.../silver/soil_analyses_normalized/`
* **Transformations Applied:** Converts mixed laboratory units (`ppm`, `%`, `g/kg`) into standardized `mg/kg` (**CA-06**).
* **Columns:** `analysis_id` (STRING), `farm_id` (STRING), `sample_date` (DATE), `original_unit` (STRING), `conversion_factor_applied` (DOUBLE), `n_mg_kg` (DOUBLE), `p_mg_kg` (DOUBLE), `k_mg_kg` (DOUBLE), `ph` (DOUBLE).

---

## PART 3: Gold Layer / Analytical Star Schema (Power BI — Section 13 & E-10)
Designed in a dimensional Star Schema (Facts & Dimensions) stored in S3 Gold (Parquet) and synced to PostgreSQL Analytics schema to answer the 6 mandatory business questions in Power BI.

### Module 3.1: Dimension Tables (5 Tables)

#### 33. Table: `dim_date`
* **Columns:** `date_key` (INT - `YYYYMMDD` PK), `full_date` (DATE), `year` (INT), `quarter` (INT), `month` (INT), `month_name` (VARCHAR), `week_of_year` (INT), `is_harvest_season` (BOOLEAN).

#### 34. Table: `dim_farm`
* **Columns:** `farm_key` (INT - Surrogate PK), `farm_id` (UUID - Natural Key), `farm_name` (VARCHAR), `producer_name` (VARCHAR), `municipality_name` (VARCHAR), `department_name` (VARCHAR), `cultivated_area_ha` (DECIMAL), `has_pilot_sensors` (BOOLEAN), `overlaps_forest_reserve` (BOOLEAN).

#### 35. Table: `dim_sensor`
* **Columns:** `sensor_key` (INT - Surrogate PK), `sensor_id` (UUID), `serial_number` (VARCHAR), `sensor_type` (VARCHAR), `farm_key` (INT), `current_health_status` (VARCHAR).

#### 36. Table: `dim_buyer`
* **Columns:** `buyer_key` (INT - Surrogate PK), `buyer_id` (UUID), `company_name` (VARCHAR), `destination_country` (VARCHAR).

#### 37. Table: `dim_alert_type`
* **Columns:** `alert_type_key` (INT - PK), `alert_code` (VARCHAR - `COFFEE_RUST`, `WATER_DEFICIT`, `EXTREME_RAIN`), `priority_weight` (INT - `3`, `2`, `1`), `rule_reference` (VARCHAR - `RN-03`, `RN-04`, `RN-05`).

---

### Module 3.2: Fact Tables (4 Tables mapped to Business Questions)

#### 38. Table: `fact_alerts_and_visits` (Answers Power BI Q1, Q2 & Q6)
* **Granularity:** One row per generated alert and its associated field visit / harvest impact.
* **Columns:** `fact_alert_visit_id` (BIGINT - PK), `date_key` (FK -> `dim_date`), `farm_key` (FK -> `dim_farm`), `alert_type_key` (FK -> `dim_alert_type`), `priority_score` (INT), `was_attended` (BOOLEAN), `visit_outcome` (VARCHAR), `days_to_attend` (INT), `harvest_yield_kg_ha` (DECIMAL), `estimated_loss_prevented_pct` (DECIMAL).

#### 39. Table: `fact_sensor_vs_satellite_climate` (Answers Power BI Q3)
* **Granularity:** One row per pilot farm per day comparing IoT ground truth against NASA POWER.
* **Columns:** `fact_climate_comp_id` (BIGINT - PK), `date_key` (FK -> `dim_date`), `farm_key` (FK -> `dim_farm`), `sensor_temp_avg_c` (DECIMAL), `satellite_temp_avg_c` (DECIMAL), `temp_delta_abs_c` (DECIMAL), `sensor_rain_mm` (DECIMAL), `satellite_rain_mm` (DECIMAL), `rain_delta_abs_mm` (DECIMAL), `used_satellite_fallback` (BOOLEAN).

#### 40. Table: `fact_batch_sustainability` (Answers Power BI Q4)
* **Granularity:** One row per export batch per contributing farm and international buyer.
* **Columns:** `fact_sustainability_id` (BIGINT - PK), `date_key` (FK -> `dim_date`), `buyer_key` (FK -> `dim_buyer`), `farm_key` (FK -> `dim_farm`), `batch_code` (VARCHAR), `contributed_weight_kg` (DECIMAL), `batch_share_pct` (DECIMAL), `weighted_water_m3_ton` (DECIMAL), `fertilizer_reduction_pct` (DECIMAL), `sca_cupping_score` (DECIMAL), `is_zero_deforestation_compliant` (BOOLEAN).

#### 41. Table: `fact_sensor_network_health_daily` (Answers Power BI Q5)
* **Granularity:** Daily snapshot of sensor statuses per farm and sensor type.
* **Columns:** `fact_health_id` (BIGINT - PK), `date_key` (FK -> `dim_date`), `farm_key` (FK -> `dim_farm`), `sensor_key` (FK -> `dim_sensor`), `active_count` (INT), `defective_stuck_count` (INT), `disconnected_count` (INT), `delayed_blocks_received_count` (INT), `avg_battery_pct` (DECIMAL).
