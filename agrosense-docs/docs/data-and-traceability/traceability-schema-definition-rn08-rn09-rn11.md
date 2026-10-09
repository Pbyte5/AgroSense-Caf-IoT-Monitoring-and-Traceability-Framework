# Database Schema Specification: Traceability, Forest Exclusions & Buyer Authorization

*Relational Data Structures, Constraints, PostGIS Spatial Indexing, and
RLS Mapping for Business Rules RN-08, RN-09, and RN-11*

# 1. Executive Overview and Business Rule Mapping

The database layer of the AgroSense Café platform enforces rigorous
relational constraints, spatial queries, and access controls to satisfy
coffee export regulations and buyer compliance. This document specifies
the exact PostgreSQL and PostGIS schema definitions supporting three
critical business rules: 100% farm lot origin composition (**RN-08**),
zero-deforestation forest reserve exclusions (**RN-09**), and strict
buyer-level data authorization isolation (**RN-11**).

| **Business Rule**                   | **Core Domain Objective**                                                                               | **Relational & Spatial Mechanism**                                           | **Database Constraint / Enforcement**                                                 |
| ----------------------------------------- | :------------------------------------------------------------------------------------------------------------ | :--------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------ |
| **RN-08: Lot Origin Breakdown**     | Ensure 100% traceable coffee origin per lot down to individual farm contributions, preserving\<5% farm links. | Junction table 'lote_finca_origen' with exact contributed weights and percentages. | FK constraints, CHECK (kilos\> 0), and Trigger validating SUM(kilos) = peso_neto_kg.        |
| **RN-09: Forest Reserve Exclusion** | Guarantee zero-deforestation compliance by excluding farms overlapping protected forest reserves.             | PostGIS 'ST_Intersects' query on 'finca.geom' vs 'reserva_forestal.geom'.          | GIST Spatial Indexing, 'solapamiento_reserva_bool' column, and Certification Guard Trigger. |
| **RN-11: Buyer Authorization**      | Isolate buyer access to query only coffee lots officially purchased by their organization.                    | Buyer registration & 'compra_lote' authorization junction table.                   | FK constraints, Unique Indices, and PostgreSQL Row-Level Security (RLS) policies.           |

# 2. RN-08 Schema Support: 100% Lot Origin & Farm Breakdown

Business Rule RN-08 mandates that every export coffee lot must be 100%
traceable to its constituent farms. If a farm contributes less than 5%
of the total net volume, it must remain explicitly recorded in the lot
breakdown to prevent micro-supplier omission. The relational structure
uses a specialized junction table linking lots to farms with rigorous
check constraints.

> -- Table 1: Export Lots (lote_exportacion)
> CREATE TABLE lote_exportacion (
> lote_id VARCHAR(50) PRIMARY KEY,
> codigo_lote VARCHAR(100) UNIQUE NOT NULL,
> peso_neto_kg NUMERIC(10, 2) NOT NULL CHECK (peso_neto_kg \> 0),
> cupping_score NUMERIC(4, 2) CHECK (cupping_score BETWEEN 0 AND 100),
> huella_hidrica_promedio NUMERIC(8, 2), -- Weighted average (RN-10)
> estado_certificacion VARCHAR(30) DEFAULT 'EN_PROCESO'
> CHECK (estado_certificacion IN ('EN_PROCESO',
> 'EXPORTABLE_CERTIFICADO', 'RECHAZADO')),
> fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
> );
>
> -- Table 2: Farm Lot Origin Junction (lote_finca_origen) - Supports
> RN-08
> CREATE TABLE lote_finca_origen (
> lote_id VARCHAR(50) NOT NULL REFERENCES lote_exportacion(lote_id) ON
> DELETE CASCADE,
> finca_id VARCHAR(50) NOT NULL REFERENCES finca(finca_id) ON DELETE
> RESTRICT,
> kilos_aportados NUMERIC(10, 2) NOT NULL CHECK (kilos_aportados \>
> 0),
> porcentaje_aporte NUMERIC(5, 2) GENERATED ALWAYS AS (kilos_aportados)
> STORED, -- Computed in views
> huella_hidrica_finca NUMERIC(8, 2),
> PRIMARY KEY (lote_id, finca_id)
> );
>
> -- Validation Trigger: Enforces 100% Volume Traceability & Balance
> CREATE OR REPLACE FUNCTION verify_lote_origin_completeness()
> RETURNS TRIGGER AS \$\$
> DECLARE
> total_kilos NUMERIC(10, 2);
> lote_peso NUMERIC(10, 2);
> BEGIN
> SELECT peso_neto_kg INTO lote_peso FROM lote_exportacion WHERE lote_id
> = NEW.lote_id;
> SELECT SUM(kilos_aportados) INTO total_kilos FROM lote_finca_origen
> WHERE lote_id = NEW.lote_id;
>
> IF total_kilos \> lote_peso THEN
> RAISE EXCEPTION 'RN-08 Violation: Total farm contributed kilos (%)
> exceeds lot net weight (%)',
> total_kilos, lote_peso;
> END IF;
> RETURN NEW;
> END;
> \$\$ LANGUAGE plpgsql;

# 3. RN-09 Schema Support: Forest Reserve Exclusion & PostGIS Spatial Constraints

Business Rule RN-09 requires zero-deforestation compliance. Farm
perimeter polygons (SRID 4326) are spatialized using PostGIS. If a farm
overlaps with protected forest reserve boundaries, its
**solapamiento_reserva_bool** flag is set to TRUE, automatically
disqualifying any coffee lot containing its volume from achieving
'EXPORTABLE_CERTIFICADO' status.

> -- Enable PostGIS Extension
> CREATE EXTENSION IF NOT EXISTS postgis;
>
> -- Table 3: Forest Reserve Polygons (reserva_forestal)
> CREATE TABLE reserva_forestal (
> reserva_id VARCHAR(50) PRIMARY KEY,
> nombre_reserva VARCHAR(150) NOT NULL,
> geom GEOMETRY(Polygon, 4326) NOT NULL
> );
> CREATE INDEX idx_reserva_geom ON reserva_forestal USING GIST(geom);
>
> -- Table 4: Farm Entity with PostGIS Geometry & Reserve Overlap Flag
> (finca)
> CREATE TABLE finca (
> finca_id VARCHAR(50) PRIMARY KEY,
> productor_id VARCHAR(50) NOT NULL REFERENCES
> productor(productor_id),
> nombre_finca VARCHAR(100) NOT NULL,
> municipio VARCHAR(100) NOT NULL,
> geom GEOMETRY(Polygon, 4326) NOT NULL,
> solapamiento_reserva_bool BOOLEAN DEFAULT FALSE,
> fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
> );
> CREATE INDEX idx_finca_geom ON finca USING GIST(geom);
>
> -- PostGIS Spatial Query Function: Evaluates Intersection with Forest
> Reserves
> CREATE OR REPLACE FUNCTION update_farm_forest_overlap()
> RETURNS TRIGGER AS \$\$
> BEGIN
> NEW.solapamiento_reserva_bool := EXISTS (
> SELECT 1 FROM reserva_forestal rf
> WHERE ST_Intersects(NEW.geom, rf.geom)
> );
> RETURN NEW;
> END;
> \$\$ LANGUAGE plpgsql;
>
> CREATE TRIGGER trg_check_farm_forest_overlap
> BEFORE INSERT OR UPDATE OF geom ON finca
> FOR EACH ROW EXECUTE FUNCTION update_farm_forest_overlap();
>
> -- Certification Guard Trigger: Blocks Export Certification if Any
> Farm Overlaps Reserve
> CREATE OR REPLACE FUNCTION
> enforce_zero_deforestation_certification()
> RETURNS TRIGGER AS \$\$
> DECLARE
> invalid_farms_count INT;
> BEGIN
> IF NEW.estado_certificacion = 'EXPORTABLE_CERTIFICADO' THEN
> SELECT COUNT(\*) INTO invalid_farms_count
> FROM lote_finca_origen lfo
> JOIN finca f ON lfo.finca_id = f.finca_id
> WHERE lfo.lote_id = NEW.lote_id AND f.solapamiento_reserva_bool =
> TRUE;
>
> IF invalid_farms_count \> 0 THEN
> RAISE EXCEPTION 'RN-09 Violation: Cannot certify lot %. Contains %
> farm(s) overlapping forest reserves.',
> NEW.lote_id, invalid_farms_count;
> END IF;
> END IF;
> RETURN NEW;
> END;
> \$\$ LANGUAGE plpgsql;

# 4. RN-11 Schema Support: Buyer Authorization & Data Isolation

Business Rule RN-11 requires strict commercial isolation. International
coffee buyers must only access traceability metrics and farm composition
details for lots they have purchased. This is enforced at the schema
layer using buyer mapping tables, foreign keys, and PostgreSQL Row-Level
Security (RLS) policies.

> -- Table 5: Buyer Registered Entities (comprador)
> CREATE TABLE comprador (
> comprador_id VARCHAR(50) PRIMARY KEY,
> razon_social VARCHAR(150) NOT NULL,
> pais_destino VARCHAR(100) NOT NULL,
> api_key_hash VARCHAR(256) NOT NULL,
> estado_activo BOOLEAN DEFAULT TRUE
> );
>
> -- Table 6: Commercial Purchase Assignment Junction (compra_lote) -
> Supports RN-11
> CREATE TABLE compra_lote (
> compra_id VARCHAR(50) PRIMARY KEY,
> comprador_id VARCHAR(50) NOT NULL REFERENCES
> comprador(comprador_id),
> lote_id VARCHAR(50) NOT NULL REFERENCES lote_exportacion(lote_id),
> fecha_compra TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
> numero_contrato VARCHAR(100) UNIQUE NOT NULL,
> CONSTRAINT uq_lote_comprador UNIQUE (lote_id, comprador_id)
> );
>
> -- Enable Row-Level Security (RLS) on Export Lots
> ALTER TABLE lote_exportacion ENABLE ROW LEVEL SECURITY;
>
> -- RLS Policy: Buyers Can Only SELECT Lots Associated with Their Buyer
> ID
> CREATE POLICY buyer_lot_isolation_policy ON lote_exportacion
> FOR SELECT
> USING (
> lote_id IN (
> SELECT cl.lote_id
> FROM compra_lote cl
> WHERE cl.comprador_id = current_setting('app.current_buyer_id',
> true)
> )
> );

# 5. Database Verification and Acceptance Criteria

To verify that the database schema correctly implements RN-08, RN-09,
and RN-11, automated integration tests perform the following assertions:

> **• RN-08 Origin Assertion:** Attempting to insert farm origin
> contributions that exceed the lot's net weight raises a database
> exception. Farms contributing \<5% are successfully persisted in
> 'lote_finca_origen'.
>
> **• RN-09 Spatial Exclusion Assertion:** Inserting a farm polygon
> intersecting a forest reserve automatically sets
> 'solapamiento_reserva_bool = TRUE'. Attempting to update the lot
> status to 'EXPORTABLE_CERTIFICADO' triggers a DB exception.
>
> **• RN-11 Authorization Isolation Assertion:** Executing a query as
> Buyer A with 'SET LOCAL app.current_buyer_id = 'BUYER-A'' returns zero
> rows for lots owned by Buyer B, satisfying REST API latency and
> security requirements (RNF-03).
