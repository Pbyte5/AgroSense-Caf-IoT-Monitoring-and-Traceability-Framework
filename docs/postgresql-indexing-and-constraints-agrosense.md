# PostgreSQL Schema Indexing & Constraint Strategy

Relational Integrity Rules, Index Optimization, and Query Performance
for 1,300 Farms & 15,000 Annual Harvest Deliveries
| **Project & Target System:** | AgroSense Café · PostgreSQL + PostGIS (Amazon EC2 Serving DB)                     |
|:-----------------------------|:----------------------------------------------------------------------------------|
| **Data Scale Profile:**      | 1,300 Farms, 300 Pilot Farms (900 IoT Sensors), ~15,000 Annual Harvest Deliveries |
| **Performance Benchmark:**   | REST API Traceability Latency p95 ≤ 500 ms (RNF-03)                               |

# 1. Executive Summary & Database Workload Profile

The PostgreSQL serving database for **AgroSense Café** manages the core
operational data for 1,300 coffee farms, 300 pilot farms with 900 IoT
sensors, and approximately 15,000 annual harvest deliveries. While
high-volume IoT sensor time-series data (130,000 daily telemetry
readings) is offloaded to the Amazon S3 Data Lake to preserve database
efficiency, the PostgreSQL relational layer must guarantee strict ACID
compliance, spatial integrity, and sub-second traceability lookups.

To satisfy requirement **RNF-03 (API response latency p95 ≤ 500 ms)**
and enforce business rules **RN-01 through RN-11**, this specification
details a comprehensive indexing and constraint strategy across primary
keys, foreign keys, spatial PostGIS geometries, check constraints, and
compound/partial indexes.

# 2. Primary Key & Unique Constraints Strategy

Primary keys and unique constraints form the foundational layer of
entity integrity in AgroSense. Every primary key implicitly generates a
unique B-Tree index in PostgreSQL, enabling O(log N) point lookups.
| **Table Name** | **Constraint Type & Columns** | **Business Purpose / Rule Enforced** |
| --- | --- | --- |
| finca | PRIMARY KEY (finca\_id)  UNIQUE (codigo\_finca) | Identifies 1,300 unique coffee farms and enforces unique cooperative registration codes. |
| entrega | PRIMARY KEY (entrega\_id)  UNIQUE (numero\_tiquete) | Enforces unique receipt ticket numbers for 15,000 annual harvest deliveries. |
| lote\_exportacion | PRIMARY KEY (lote\_id)  UNIQUE (codigo\_lote) | Guarantees unique export lot identifiers for international coffee buyers (RN-08, RF-06). |
| lote\_finca\_origen | PRIMARY KEY (lote\_id, finca\_id) | Composite primary key for N:M join table, preventing duplicate farm allocation entries per lot. |
| compra\_lote | PRIMARY KEY (compra\_id)  UNIQUE (lote\_id, comprador\_id) | Guarantees single purchase contract mapping between an export lot and a buyer (RN-11). |


# 3. Foreign Key Integrity & Referential Actions

Foreign key constraints prevent orphaned records and enforce strict
domain boundaries. In PostgreSQL, foreign keys do **NOT** automatically
create indexes. Therefore, explicit B-Tree lookup indexes are defined on
all foreign key columns to eliminate sequential table scans during join
operations and cascade validation checks.
| **Child Table**   | **Foreign Key Column** | **Parent Table (Ref)** | **Referential Action & Rationale**                                                        |
|:------------------|:-----------------------|:-----------------------|:------------------------------------------------------------------------------------------|
| entrega           | finca_id               | finca(finca_id)        | ON DELETE RESTRICT: Prevents deletion of a farm if active harvest deliveries exist.       |
| analisis_suelo    | finca_id               | finca(finca_id)        | ON DELETE CASCADE: Deletes historical soil reports if farm record is purged.              |
| lote_finca_origen | lote_id                | lote_exportacion       | ON DELETE CASCADE: Removes lot-farm composition links if lot is deleted.                  |
| lote_finca_origen | finca_id               | finca(finca_id)        | ON DELETE RESTRICT: Prevents farm deletion if coffee kilos are assigned to an export lot. |
| compra_lote       | comprador_id           | comprador              | ON DELETE RESTRICT: Protects buyer purchase records from accidental deletion (RN-11).     |

# 4. Domain Check Constraints & Business Rule Validation

Check constraints enforce domain integrity at the database layer,
guaranteeing that invalid data is rejected regardless of whether the
insertion originates from FastAPI, PySpark ETL, or seed scripts.
| **Table Name**    | **Check Constraint Definition**                                                       | **Business Rule & Validation Target**                                                      |
|:------------------|:--------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------|
| entrega           | CHECK (kilos_pesados \> 0 AND factor_rendimiento \> 0)                                | Ensures positive harvest delivery weight and valid yield factor calculations.              |
| lote_exportacion  | CHECK (peso_neto_kg \> 0 AND cupping_score BETWEEN 0 AND 100)                         | Validates positive net weight and standard Specialty Coffee Association (SCA) score range. |
| lote_exportacion  | CHECK (estado_certificacion IN ('EN_PROCESO', 'EXPORTABLE_CERTIFICADO', 'RECHAZADO')) | Restricts lot certification status enum values (RN-08, RN-09).                             |
| lote_finca_origen | CHECK (kilos_aportados \> 0)                                                          | Guarantees positive weight contribution per farm in coffee lot blending.                   |
| analisis_suelo    | CHECK (ph BETWEEN 3.5 AND 9.0 AND materia_organica_pct \>= 0)                         | Enforces realistic agronomical boundaries for soil laboratory reports (RN-07).             |

# 5. Specialized Indexing Strategy for Query Optimization

To achieve sub-500ms latency across 15,000 annual deliveries and spatial
polygon overlaps, PostgreSQL is configured with specialized spatial GiST
indexes, compound B-Trees for multi-column filtering, and partial
indexes for active records.
| **Index Name**          | **Target Table & Columns**                             | **Index Type**  | **Query Optimization Target**                                                                    |
|:------------------------|:-------------------------------------------------------|:----------------|:-------------------------------------------------------------------------------------------------|
| idx_finca_geom          | finca(geom)                                            | Spatial GiST    | Accelerates PostGIS ST_Intersects queries for zero deforestation reserve overlap checks (RN-09). |
| idx_reserva_geom        | reserva_forestal(geom)                                 | Spatial GiST    | Optimizes spatial intersection checks against protected national forest boundaries.              |
| idx_entrega_finca_fecha | entrega(finca_id, fecha_entrega DESC)                  | Compound B-Tree | Accelerates farm harvest history filtering and chronological delivery sorting.                   |
| idx_compra_comprador    | compra_lote(comprador_id, fecha_compra DESC)           | Compound B-Tree | Optimizes API buyer lot isolation queries and contract history lookups (RN-11).                  |
| idx_finca_reserva_flag  | finca(finca_id) WHERE solapamiento_reserva_bool = TRUE | Partial B-Tree  | Fast lookup for invalidated farms overlapping forest reserves without scanning compliant farms.  |

# 6. Complete SQL DDL Indexing & Constraint Statements

The following SQL DDL script consolidates all index creations and
constraint definitions for deployment via Alembic migrations:

-- 1. Foreign Key B-Tree Lookup Indexes  
CREATE INDEX IF NOT EXISTS idx_fk_entrega_finca ON entrega(finca_id);  
CREATE INDEX IF NOT EXISTS idx_fk_analisis_suelo_finca ON
analisis_suelo(finca_id);  
CREATE INDEX IF NOT EXISTS idx_fk_lfo_lote ON
lote_finca_origen(lote_id);  
CREATE INDEX IF NOT EXISTS idx_fk_lfo_finca ON
lote_finca_origen(finca_id);  
CREATE INDEX IF NOT EXISTS idx_fk_compra_comprador ON
compra_lote(comprador_id);  
  
-- 2. PostGIS Spatial GiST Indexes  
CREATE INDEX IF NOT EXISTS idx_finca_geom ON finca USING GIST(geom);  
CREATE INDEX IF NOT EXISTS idx_reserva_geom ON reserva_forestal USING
GIST(geom);  
  
-- 3. Compound B-Tree Filtering & Sorting Indexes  
CREATE INDEX IF NOT EXISTS idx_entrega_finca_fecha ON entrega(finca_id,
fecha_entrega DESC);  
CREATE INDEX IF NOT EXISTS idx_compra_comprador_fecha ON
compra_lote(comprador_id, fecha_compra DESC);  
  
-- 4. Partial Indexes for High-Frequency Conditional Queries  
CREATE INDEX IF NOT EXISTS idx_finca_invalidated_reserve ON
finca(finca_id)  
WHERE solapamiento_reserva_bool = TRUE;  
  
CREATE INDEX IF NOT EXISTS idx_lote_certified_exportable ON
lote_exportacion(lote_id)  
WHERE estado_certificacion = 'EXPORTABLE_CERTIFICADO';
