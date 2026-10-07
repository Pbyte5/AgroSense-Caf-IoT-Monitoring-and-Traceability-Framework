# 🗄️ AgroSense Café — Diccionario de Datos Relacional y Especificación de Columnas

Este documento define la especificación técnica a nivel de columna para la base de datos relacional (**PostgreSQL 16+**) de **AgroSense Café**. Sirve como plano de implementación para migraciones de esquemas (Alembic / SQLAlchemy), restricciones de integridad e indexación.

---

## Convenciones Generales del Esquema

- **Motor de Base de Datos:** PostgreSQL 16+
- **Extensión de UUID:** Se requiere `pgcrypto` (`gen_random_uuid()`) para llaves primarias distribuidas.
- **Zona Horaria:** Todas las marcas de tiempo utilizan `TIMESTAMPTZ` almacenadas en UTC.
- **Nomenclatura:** `snake_case` estricto para nombres de tablas, columnas, índices y restricciones.

---

## MÓDULO 1: Core & Fincas

### 1.1 Tabla: `departments`
Catálogo geográfico de departamentos productores de café.

| Nombre del Campo | Tipo de Dato SQL | PK | FK | Nullability | Default | Notas y Restricciones (CHECK / Constraints) |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| `department_id` | `SERIAL` | ✅ | — | `NOT NULL` | `nextval()` | Identificador único del departamento. |
| `dane_code` | `VARCHAR(5)` | — | — | `NOT NULL` | — | `UNIQUE`. Código oficial administrativo (ej. `'05'`, `'17'`). |
| `name` | `VARCHAR(100)` | — | — | `NOT NULL` | — | `UNIQUE`. Nombre oficial del departamento. |
| `created_at` | `TIMESTAMPTZ` | — | — | `NOT NULL` | `CURRENT_TIMESTAMP` | Fecha de creación del registro. |

> **Notas de tabla:** Tabla dimensional estática de baja cardinalidad; indexada por `dane_code`.

---

### 1.2 Tabla: `municipalities`
Catálogo de municipios cafeteros asociados a un departamento (Fuente F1).

| Nombre del Campo | Tipo de Dato SQL | PK | FK | Nullability | Default | Notas y Restricciones (CHECK / Constraints) |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| `municipality_id` | `SERIAL` | ✅ | — | `NOT NULL` | `nextval()` | Identificador único del municipio. |
| `department_id` | `INTEGER` | — | `REFERENCES departments(department_id)` | `NOT NULL` | — | `ON DELETE RESTRICT`. |
| `dane_code` | `VARCHAR(10)` | — | — | `NOT NULL` | — | `UNIQUE`. Código oficial del municipio. |
| `name` | `VARCHAR(120)` | — | — | `NOT NULL` | — | Nombre del municipio. |
| `altitude_avg_masl` | `INTEGER` | — | — | `NULL` | `NULL` | `CHECK (altitude_avg_masl BETWEEN 400 AND 3000)`. Altitud promedio en m.s.n.m. |
| `created_at` | `TIMESTAMPTZ` | — | — | `NOT NULL` | `CURRENT_TIMESTAMP` | Fecha de registro. |

> **Notas de tabla:** Índice compuesto en `(department_id, name)`.

---

### 1.3 Tabla: `coffee_varieties`
Catálogo de variedades de café cultivadas en la cooperativa y su resistencia biológica a plagas.

| Nombre del Campo | Tipo de Dato SQL | PK | FK | Nullability | Default | Notas y Restricciones (CHECK / Constraints) |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| `variety_id` | `SERIAL` | ✅ | — | `NOT NULL` | `nextval()` | Identificador único de la variedad. |
| `name` | `VARCHAR(80)` | — | — | `NOT NULL` | — | `UNIQUE` (ej. `'Castillo'`, `'Caturra'`, `'Geisha'`, `'Tabi'`). |
| `rust_resistance_level` | `VARCHAR(20)` | — | — | `NOT NULL` | `'MEDIUM'` | `CHECK (rust_resistance_level IN ('LOW', 'MEDIUM', 'HIGH'))`. Nivel de resistencia a la roya. |
| `optimal_temp_min_c` | `NUMERIC(4,1)` | — | — | `NOT NULL` | `17.0` | `CHECK (optimal_temp_min_c >= 10.0)`. Temperatura mínima ideal (°C). |
| `optimal_temp_max_c` | `NUMERIC(4,1)` | — | — | `NOT NULL` | `24.0` | `CHECK (optimal_temp_max_c <= 35.0)`. Temperatura máxima ideal (°C). |

> **Notas de tabla:** Utilizada en las reglas agronómicas para ponderar la vulnerabilidad del lote frente a alertas de roya.

---

### 1.4 Tabla: `farms`
Registro maestro de las 1.300 fincas afiliadas a la cooperativa (Fuente F1).

| Nombre del Campo | Tipo de Dato SQL | PK | FK | Nullability | Default | Notas y Restricciones (CHECK / Constraints) |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| `farm_id` | `UUID` | ✅ | — | `NOT NULL` | `gen_random_uuid()` | Identificador único universal de la finca. |
| `farm_code` | `VARCHAR(20)` | — | — | `NOT NULL` | — | `UNIQUE`. Código interno de la cooperativa (ej. `'FIN-0042'`). |
| `municipality_id` | `INTEGER` | — | `REFERENCES municipalities(municipality_id)` | `NOT NULL` | — | Municipio donde se ubica la finca. |
| `name` | `VARCHAR(150)` | — | — | `NOT NULL` | — | Nombre de la finca. |
| `producer_name` | `VARCHAR(150)` | — | — | `NOT NULL` | — | Nombre completo del caficultor titular. |
| `latitude` | `NUMERIC(9,6)` | — | — | `NOT NULL` | — | `CHECK (latitude BETWEEN -4.23 AND 13.50)`. Coordenada geográfica latitud. |
| `longitude` | `NUMERIC(9,6)` | — | — | `NOT NULL` | — | `CHECK (longitude BETWEEN -81.73 AND -66.85)`. Coordenada geográfica longitud. |
| `altitude_masl` | `INTEGER` | — | — | `NOT NULL` | — | `CHECK (altitude_masl BETWEEN 800 AND 2600)`. Altitud en m.s.n.m. |
| `total_area_ha` | `NUMERIC(8,2)` | — | — | `NOT NULL` | — | `CHECK (total_area_ha > 0)`. Hectáreas totales del predio. |
| `is_pilot_sensor_farm` | `BOOLEAN` | — | — | `NOT NULL` | `FALSE` | Indica si pertenece al grupo de 300 fincas piloto con sensores IoT. |
| `is_active` | `BOOLEAN` | — | — | `NOT NULL` | `TRUE` | Estado activo de la finca en la cooperativa. |
| `created_at` | `TIMESTAMPTZ` | — | — | `NOT NULL` | `CURRENT_TIMESTAMP` | Fecha de alta en el sistema. |

> **Notas de tabla:** Índices en `farm_code`, `municipality_id` e índice espacial/compuesto en `(latitude, longitude)` para cruces climáticos satelitales (NASA POWER / Open-Meteo).

---

### 1.5 Tabla: `farm_plots`
Subdivisión productiva (lotes internos o tablones) dentro de cada finca.

| Nombre del Campo | Tipo de Dato SQL | PK | FK | Nullability | Default | Notas y Restricciones (CHECK / Constraints) |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| `plot_id` | `UUID` | ✅ | — | `NOT NULL` | `gen_random_uuid()` | Identificador único del lote interno de la finca. |
| `farm_id` | `UUID` | — | `REFERENCES farms(farm_id)` | `NOT NULL` | — | `ON DELETE CASCADE`. Finca a la que pertenece el lote. |
| `variety_id` | `INTEGER` | — | `REFERENCES coffee_varieties(variety_id)` | `NOT NULL` | — | Variedad sembrada en el lote. |
| `plot_number` | `INTEGER` | — | — | `NOT NULL` | — | `CHECK (plot_number > 0)`. Número secuencial dentro de la finca. |
| `cultivated_area_ha` | `NUMERIC(7,2)` | — | — | `NOT NULL` | — | `CHECK (cultivated_area_ha > 0)`. Área cultivada en hectáreas. |
| `tree_density_per_ha` | `INTEGER` | — | — | `NOT NULL` | `5000` | `CHECK (tree_density_per_ha BETWEEN 1000 AND 12000)`. Árboles por hectárea. |
| `planting_date` | `DATE` | — | — | `NULL` | `NULL` | Fecha de siembra o última renovación por zoca. |

> **Notas de tabla:** Restricción `UNIQUE (farm_id, plot_number)` para evitar lotes duplicados en una misma finca.

---

## MÓDULO 2: IoT & Telemetría

### 2.1 Tabla: `iot_sensors`
Inventario y estado de los sensores instalados en las 300 fincas piloto (Fuente F4).

| Nombre del Campo | Tipo de Dato SQL | PK | FK | Nullability | Default | Notas y Restricciones (CHECK / Constraints) |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| `sensor_id` | `UUID` | ✅ | — | `NOT NULL` | `gen_random_uuid()` | Identificador único del dispositivo IoT. |
| `serial_number` | `VARCHAR(50)` | — | — | `NOT NULL` | — | `UNIQUE`. Serial físico del fabricante. |
| `farm_id` | `UUID` | — | `REFERENCES farms(farm_id)` | `NOT NULL` | — | Finca donde está instalado el sensor. |
| `plot_id` | `UUID` | — | `REFERENCES farm_plots(plot_id)` | `NULL` | `NULL` | Lote específico monitoreado. |
| `sensor_type` | `VARCHAR(30)` | — | — | `NOT NULL` | `'MULTI_AGRO'` | `CHECK (sensor_type IN ('SOIL_MOISTURE', 'TEMPERATURE', 'PLUVIOMETER', 'MULTI_AGRO'))`. |
| `firmware_version` | `VARCHAR(20)` | — | — | `NOT NULL` | `'v1.0.0'` | Versión actual del firmware del nodo. |
| `status` | `VARCHAR(20)` | — | — | `NOT NULL` | `'ACTIVE'` | `CHECK (status IN ('ACTIVE', 'OFFLINE', 'MAINTENANCE', 'RETIRED'))`. |
| `last_seen_at` | `TIMESTAMPTZ` | — | — | `NULL` | `NULL` | Última marca de tiempo de sincronización por red celular (ACK). |
| `installed_at` | `DATE` | — | — | `NOT NULL` | `CURRENT_DATE` | Fecha de instalación en campo. |

> **Notas de tabla:** Soporta RNF-01 mediante el seguimiento de `last_seen_at` para detectar sensores desconectados hasta por 7 días.

---

### 2.2 Tabla: `sensor_anomalies_log`
Registro de auditoría para lecturas descartadas o marcadas como anómalas durante el paso de la capa Bronze a Silver.

| Nombre del Campo | Tipo de Dato SQL | PK | FK | Nullability | Default | Notas y Restricciones (CHECK / Constraints) |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| `anomaly_id` | `BIGSERIAL` | ✅ | — | `NOT NULL` | `nextval()` | Identificador secuencial del evento anómalo. |
| `sensor_id` | `UUID` | — | `REFERENCES iot_sensors(sensor_id)` | `NOT NULL` | — | Sensor que originó la lectura defectuosa. |
| `reading_timestamp` | `TIMESTAMPTZ` | — | — | `NOT NULL` | — | Marca de tiempo original de la lectura en el campo. |
| `received_at` | `TIMESTAMPTZ` | — | — | `NOT NULL` | `CURRENT_TIMESTAMP` | Momento en que la cola IoT recibió el bloque atrasado. |
| `anomaly_type` | `VARCHAR(40)` | — | — | `NOT NULL` | — | `CHECK (anomaly_type IN ('OUT_OF_RANGE', 'DUPLICATE_BLOCK', 'STALE_OVER_7_DAYS', 'NULL_PAYLOAD'))`. |
| `raw_payload` | `JSONB` | — | — | `NOT NULL` | — | Lectura cruda recibida para diagnóstico técnico. |

> **Notas de tabla:** Las series de tiempo limpias residen en el Data Lake (Parquet particionado por día); esta tabla relacional solo registra fallos de calidad de datos para mantenimiento de hardware.

---

## MÓDULO 3: Suelos & Nutrición

### 3.1 Tabla: `soil_lab_analyses`
Resultados fisicoquímicos de laboratorio por lote (Fuente F5).

| Nombre del Campo | Tipo de Dato SQL | PK | FK | Nullability | Default | Notas y Restricciones (CHECK / Constraints) |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| `analysis_id` | `UUID` | ✅ | — | `NOT NULL` | `gen_random_uuid()` | Identificador único del análisis de suelo. |
| `plot_id` | `UUID` | — | `REFERENCES farm_plots(plot_id)` | `NOT NULL` | — | Lote evaluado. |
| `sample_date` | `DATE` | — | — | `NOT NULL` | — | Fecha de toma de la muestra en campo. |
| `ph_level` | `NUMERIC(4,2)` | — | — | `NOT NULL` | — | `CHECK (ph_level BETWEEN 3.00 AND 9.50)`. Acidez del suelo. |
| `organic_matter_pct` | `NUMERIC(5,2)` | — | — | `NOT NULL` | — | `CHECK (organic_matter_pct BETWEEN 0.00 AND 100.00)`. Porcentaje de materia orgánica. |
| `nitrogen_ppm` | `NUMERIC(7,2)` | — | — | `NOT NULL` | — | `CHECK (nitrogen_ppm >= 0)`. Nitrógeno disponible (ppm). |
| `phosphorus_ppm` | `NUMERIC(7,2)` | — | — | `NOT NULL` | — | `CHECK (phosphorus_ppm >= 0)`. Fósforo disponible (ppm). |
| `potassium_cmol_kg` | `NUMERIC(6,2)` | — | — | `NOT NULL` | — | `CHECK (potassium_cmol_kg >= 0)`. Potasio intercambiable (cmol/kg). |
| `soil_texture` | `VARCHAR(30)` | — | — | `NOT NULL` | — | `CHECK (soil_texture IN ('SANDY', 'LOAM', 'CLAY_LOAM', 'CLAY', 'SILTY'))`. |

> **Notas de tabla:** Índice en `(plot_id, sample_date DESC)` para obtener rápidamente el análisis vigente de cada lote.

---

### 3.2 Tabla: `crop_nutrient_references`
Parámetros agronómicos ideales de nutrición según variedad y etapa fenológica para evitar fertilización genérica.

| Nombre del Campo | Tipo de Dato SQL | PK | FK | Nullability | Default | Notas y Restricciones (CHECK / Constraints) |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| `reference_id` | `SERIAL` | ✅ | — | `NOT NULL` | `nextval()` | Identificador único de la regla nutricional. |
| `variety_id` | `INTEGER` | — | `REFERENCES coffee_varieties(variety_id)` | `NOT NULL` | — | Variedad de café aplicable. |
| `growth_stage` | `VARCHAR(30)` | — | — | `NOT NULL` | — | `CHECK (growth_stage IN ('VEGETATIVE', 'FLOWERING', 'GRAIN_FILLING', 'POST_HARVEST'))`. |
| `target_ph_min` | `NUMERIC(4,2)` | — | — | `NOT NULL` | `5.00` | `CHECK (target_ph_min >= 4.00)`. pH mínimo recomendado. |
| `target_ph_max` | `NUMERIC(4,2)` | — | — | `NOT NULL` | `5.80` | `CHECK (target_ph_max <= 7.00)`. pH máximo recomendado. |
| `req_nitrogen_kg_ha` | `NUMERIC(6,2)` | — | — | `NOT NULL` | — | `CHECK (req_nitrogen_kg_ha >= 0)`. Requerimiento de N por hectárea. |
| `req_phosphorus_kg_ha` | `NUMERIC(6,2)` | — | — | `NOT NULL` | — | `CHECK (req_phosphorus_kg_ha >= 0)`. Requerimiento de P por hectárea. |
| `req_potassium_kg_ha` | `NUMERIC(6,2)` | — | — | `NOT NULL` | — | `CHECK (req_potassium_kg_ha >= 0)`. Requerimiento de K por hectárea. |

> **Notas de tabla:** Restricción `UNIQUE (variety_id, growth_stage)`.

---

### 3.3 Tabla: `fertilizer_recommendations`
Planes de fertilización calculados por finca/lote para alcanzar el objetivo de reducción del 20% en insumos químicos.

| Nombre del Campo | Tipo de Dato SQL | PK | FK | Nullability | Default | Notas y Restricciones (CHECK / Constraints) |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| `recommendation_id` | `UUID` | ✅ | — | `NOT NULL` | `gen_random_uuid()` | Identificador único de la recomendación. |
| `plot_id` | `UUID` | — | `REFERENCES farm_plots(plot_id)` | `NOT NULL` | — | Lote objetivo. |
| `analysis_id` | `UUID` | — | `REFERENCES soil_lab_analyses(analysis_id)` | `NOT NULL` | — | Análisis de suelo que respalda el cálculo. |
| `generated_at` | `TIMESTAMPTZ` | — | — | `NOT NULL` | `CURRENT_TIMESTAMP` | Fecha de generación por el motor de reglas (Gold). |
| `recommended_n_kg_ha` | `NUMERIC(6,2)` | — | — | `NOT NULL` | — | `CHECK (recommended_n_kg_ha >= 0)`. Dosis ajustada de Nitrógeno. |
| `recommended_p_kg_ha` | `NUMERIC(6,2)` | — | — | `NOT NULL` | — | `CHECK (recommended_p_kg_ha >= 0)`. Dosis ajustada de Fósforo. |
| `recommended_k_kg_ha` | `NUMERIC(6,2)` | — | — | `NOT NULL` | — | `CHECK (recommended_k_kg_ha >= 0)`. Dosis ajustada de Potasio. |
| `lime_amendment_kg_ha` | `NUMERIC(7,2)` | — | — | `NOT NULL` | `0.00` | `CHECK (lime_amendment_kg_ha >= 0)`. Cal requerida si el pH es muy ácido. |
| `estimated_saving_pct` | `NUMERIC(5,2)` | — | — | `NOT NULL` | `0.00` | `CHECK (estimated_saving_pct BETWEEN -100.00 AND 100.00)`. Ahorro frente a dosis genérica tradicional. |
| `status` | `VARCHAR(20)` | — | — | `NOT NULL` | `'PENDING'` | `CHECK (status IN ('PENDING', 'APPLIED', 'EXPIRED'))`. |

> **Notas de tabla:** Alimenta los indicadores de sostenibilidad por lote y el tablero de gestión agronómica.

---

## MÓDULO 4: Alertas & Visitas

### 4.1 Tabla: `agronomic_alerts`
Alertas tempranas generadas con $\ge$ 5 días de anticipación antes de las 05:00 a. m. (RNF-02).

| Nombre del Campo | Tipo de Dato SQL | PK | FK | Nullability | Default | Notas y Restricciones (CHECK / Constraints) |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| `alert_id` | `UUID` | ✅ | — | `NOT NULL` | `gen_random_uuid()` | Identificador único de la alerta. |
| `farm_id` | `UUID` | — | `REFERENCES farms(farm_id)` | `NOT NULL` | —