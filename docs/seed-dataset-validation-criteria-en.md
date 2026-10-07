# Validation Criteria for Seed Output & Synthetic Dataset Quality

*AgroSense Café — Deliverables E-03, CT-06 \| Jira Tasks AGRO-04A,
AGRO-04B, AGRO-05C*

# 1. Document Purpose and Scope

This document establishes the quantitative criteria, verification rules,
and automated inspection protocols required to validate the output of
the seed script and synthetic dataset for the AgroSense Café platform.
The objective is to certify that simulated data generation is fully
reproducible, maintains domain integrity, and properly injects
controlled data quality defects to test the resilience of downstream
processing pipelines.

### Core Technical Pillars (Deliverables E-03 & CT-06):

- **Deterministic Reproducibility:** Utilizing a fixed random seed
  (SEED=42) guarantees that independent executions generate identical
  records, spatial coordinates, and telemetry metrics.

- **Strict Idempotency (CT-06):** Re-running the seed script against an
  existing database does not duplicate keys, corrupt sequence IDs, or
  inflate row counts, utilizing native UPSERT / ON CONFLICT logic.

- **Volume Parameterization:** Supports dynamic switching between a
  compact development volume (mode=dev) for rapid local testing and a
  full production simulation (mode=full).

- **Configurable Defect Injection:** Deliberately introduces controlled
  data quality anomalies with a configurable defect rate (DEFECT_RATE)
  to validate business rule enforcement (RN-01 through RN-11).

# 2. Quality Criteria Matrix

| **Category**         | **Target Metric / Rule**                                   | **Acceptance Criterion (Verifiable)**                                                | **Validation Method**    |
|:---------------------|:-----------------------------------------------------------|:-------------------------------------------------------------------------------------|:-------------------------|
| Completeness (dev)   | 50 farms, ~500 deliveries                                  | 100% match in record counts with zero NULL primary keys.                             | SQL Count / Pandas len() |
| Completeness (full)  | 1,300 farms, 300 pilot (900 sensors), ~15k deliveries/year | Full volume populated covering all domain entities.                                  | pytest Assertion Script  |
| Relational Integrity | Foreign Key constraints & coherent catalog                 | Zero orphan records. All deliveries, lots, and sensors map to valid parent entities. | SQL Foreign Key Checks   |
| Spatial Integrity    | PostGIS SRID 4326 & valid geometries                       | ST_IsValid(geom) = True for 100% of farm polygons in coffee region.                  | PostGIS ST_IsValid Query |
| Idempotency (CT-06)  | UPSERT / ON CONFLICT execution                             | Re-running seed script produces identical row counts without primary key conflicts.  | MD5 Table Checksum       |
| Reproducibility      | Fixed Seed (SEED=42)                                       | Two independent executions generate exact identical dataset hashes.                  | Direct Hash Comparison   |

# 3. Validation Criteria for Injected Quality Defects (Section 5.3)

To verify that downstream pipelines correctly handle real-world
telemetry anomalies, the synthetic dataset generator injects six
controlled defect scenarios at a configurable rate:

| **Defect ID** | **Injected Anomaly (Sec. 5.3)**            | **Business Rule / Criterion** | **Dataset Validation Criterion**                                                                |
|:--------------|:-------------------------------------------|:------------------------------|:------------------------------------------------------------------------------------------------|
| DEF-01        | Lagged / out-of-order sensor timestamps    | RN-01 & CA-01                 | Confirm readings are sorted by device_timestamp and correctly slotted into ±15 min window.      |
| DEF-02        | Flatlining sensor (variance \<0.5% in 24h) | RN-02 & CA-02                 | Verify variance query flags sensor as DEFECTIVE and excludes it from alert processing.          |
| DEF-03        | Inverted / out-of-bounds coordinates       | PostGIS ST_Contains           | Confirm spatial validation isolates farm polygons located outside Colombia coffee bounding box. |
| DEF-04        | Mixed lab units (ppm vs mg/kg)             | RN-07 & CA-06                 | Validate unit normalizer handles both inputs producing identical fertilization recommendations. |
| DEF-05        | Export lots with untraceable farm origin   | RN-08 & CA-07                 | Confirm system blocks EXPORTABLE status unless 100% of kilos are traced to registered farms.    |
| DEF-06        | Farm polygon overlap with forest reserve   | RN-09 & CA-08                 | Verify ST_Intersects detects overlap and rejects farm contribution from certified export lots.  |

# 4. Automated Verification Inspection Snippets (SQL & pytest)

**SQL Inspections for Relational, Spatial, and Sensor Quality
Integrity:**

-- 1. Foreign Key Integrity Check (Zero Orphan Deliveries)  
SELECT COUNT(\*) AS orphan_deliveries_count  
FROM delivery d  
LEFT JOIN farm f ON d.farm_id = f.farm_id  
WHERE f.farm_id IS NULL;  
  
-- 2. PostGIS Geometry Validity & SRID Check  
SELECT farm_id, name  
FROM farm  
WHERE ST_IsValid(geom) = FALSE OR ST_SRID(geom) != 4326;  
  
-- 3. Detection of Flatlining / Defective Sensors (RN-02)  
SELECT sensor_id, STDDEV(reading_value)  
FROM sensor_reading  
WHERE reading_timestamp \>= NOW() - INTERVAL '24 hours'  
GROUP BY sensor_id  
HAVING STDDEV(reading_value) \< 0.005;

### Automated Idempotency Assertion Test (pytest / CT-06):

def test_seed_idempotency_ct06():  
run_seed(seed_value=42, mode='dev') \# Initial execution  
hash_run_1 = calculate_database_checksum()  
  
run_seed(seed_value=42, mode='dev') \# Re-execution (UPSERT)  
hash_run_2 = calculate_database_checksum()  
  
assert hash_run_1 == hash_run_2, 'Assertion Error: Seed execution is not
idempotent (CT-06 violation)'

# 5. Dataset Certification Checklist

- **\[X\]** Deterministic seed confirmed (SEED=42) yielding identical
  hashes across runs.

- **\[X\]** Strict idempotency verified: double execution causes no key
  conflicts or row inflation (CT-06).

- **\[X\]** Volume parameterization validated for both mode=dev and
  mode=full.

- **\[X\]** PostGIS ST_IsValid returns TRUE for 100% of synthetic farm
  polygons.

- **\[X\]** Controlled defect injection (DEF-01 to DEF-06) verified
  within configured DEFECT_RATE bounds.

- **\[X\]** Zero hardcoded secrets or credentials present in seed
  scripts (CT-02 compliance).
