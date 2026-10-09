# 🐍 AgroSense Café — Especificación de Mapeo ORM (SQLAlchemy 2.0)

Este documento define el diseño técnico y la implementación de los modelos ORM en **SQLAlchemy 2.0** para el backend en **FastAPI** de **AgroSense Café**. Traduce el Diccionario de Datos Relacional (`RELATIONAL_DATA_DICTIONARY.md`) a clases tipadas de Python utilizando `Mapped`, `mapped_column` y `relationship`.

---

## 1. Convenciones de Nomenclatura (Naming Conventions)

| Elemento | Convención | Ejemplo |
| :--- | :--- | :--- |
| **Clases de Modelo (Python)** | Singular en `PascalCase` | `Farm`, `FarmPlot`, `IoTSensor`, `AgronomicAlert` |
| **Nombres de Tablas (PostgreSQL)** | Plural en `snake_case` | `__tablename__ = "farms"`, `"iot_sensors"` |
| **Columnas y Atributos** | `snake_case` con Type Hints | `farm_id: Mapped[uuid.UUID]`, `cultivation_area_ha: Mapped[Decimal]` |
| **Relaciones (`relationship`)** | `snake_case` (plural para `1:N`, singular para `N:1`) | `plots: Mapped[list["FarmPlot"]]`, `farm: Mapped["Farm"]` |
| **Restricciones (`CheckConstraint` / `UniqueConstraint`)** | Prefijos estándar (`ck_`, `uq_`, `ix_`) | `uq_farm_plots_farm_plot_number`, `ck_farms_latitude_range` |

---

## 2. Arquitectura Modular del Proyecto (`app/models/`)

Los modelos se organizan por dominio funcional dentro del paquete `app/models/` para evitar importaciones circulares y facilitar el mantenimiento con **Alembic**:

```text
app/
└── models/
    ├── __init__.py          # Exporta Base y todos los modelos para autogeneración de Alembic
    ├── base.py              # DeclarativeBase, BaseModel (UUID) y TimestampMixin
    ├── location.py          # Department, Municipality
    ├── farm.py              # CoffeeVariety, Farm, FarmPlot
    ├── iot.py               # IoTSensor, SensorAnomaliesLog
    ├── soil.py              # SoilLabAnalysis, CropNutrientReference, FertilizerRecommendation
    ├── alerts.py            # AgronomicAlert, AgronomistFieldVisit
    ├── traceability.py      # ForestReserve, FarmReserveOverlap, ExportBatch, BatchFarmComposition
    └── buyers.py            # InternationalBuyer, BuyerBatchContract, BuyerApiAuditLog
```

---

## 3. Resumen de Mapeo de Entidades y Cardinalidad

| Módulo | Clase Python (ORM) | Tabla SQL (`__tablename__`) | PK | Relaciones Principales y Cardinalidad |
| :--- | :--- | :--- | :--- | :--- |
| `location.py` | `Department` | `departments` | `SERIAL` | `1:N` con `Municipality` (`municipalities`) |
| `location.py` | `Municipality` | `municipalities` | `SERIAL` | `N:1` con `Department`, `1:N` con `Farm` (`farms`) |
| `farm.py` | `CoffeeVariety` | `coffee_varieties` | `SERIAL` | `1:N` con `FarmPlot`, `1:N` con `CropNutrientReference` |
| `farm.py` | `Farm` | `farms` | `UUID` | `1:N` con `FarmPlot`, `IoTSensor`, `AgronomicAlert`, `AgronomistFieldVisit`, `FarmReserveOverlap`, `BatchFarmComposition` |
| `farm.py` | `FarmPlot` | `farm_plots` | `UUID` | `N:1` con `Farm` y `CoffeeVariety`; `1:N` con `SoilLabAnalysis`, `FertilizerRecommendation` |
| `iot.py` | `IoTSensor` | `iot_sensors` | `UUID` | `N:1` con `Farm` y `FarmPlot`; `1:N` con `SensorAnomaliesLog` |
| `iot.py` | `SensorAnomaliesLog` | `sensor_anomalies_log` | `BIGSERIAL` | `N:1` con `IoTSensor` |
| `soil.py` | `SoilLabAnalysis` | `soil_lab_analyses` | `UUID` | `N:1` con `FarmPlot`; `1:N` con `FertilizerRecommendation` |
| `soil.py` | `CropNutrientReference` | `crop_nutrient_references` | `SERIAL` | `N:1` con `CoffeeVariety` |
| `soil.py` | `FertilizerRecommendation` | `fertilizer_recommendations` | `UUID` | `N:1` con `FarmPlot` y `SoilLabAnalysis` |
| `alerts.py` | `AgronomicAlert` | `agronomic_alerts` | `UUID` | `N:1` con `Farm` y `FarmPlot`; `1:N` con `AgronomistFieldVisit` |
| `alerts.py` | `AgronomistFieldVisit` | `agronomist_field_visits` | `UUID` | `N:1` con `Farm` y `AgronomicAlert` |
| `traceability.py` | `ForestReserve` | `forest_reserves` | `UUID` | `1:N` con `FarmReserveOverlap` (Asociación `M:N` con `Farm`) |
| `traceability.py` | `FarmReserveOverlap` | `farm_reserve_overlaps` | `UUID` | Objeto de asociación entre `Farm` y `ForestReserve` |
| `traceability.py` | `ExportBatch` | `export_batches` | `UUID` | `1:N` con `BatchFarmComposition`, `BuyerBatchContract`, `BuyerApiAuditLog` |
| `traceability.py` | `BatchFarmComposition` | `batch_farm_compositions` | `UUID` | Objeto de asociación `M:N` entre `ExportBatch`, `Farm` y `FarmPlot` |
| `buyers.py` | `InternationalBuyer` | `international_buyers` | `UUID` | `1:N` con `BuyerBatchContract` y `BuyerApiAuditLog` |
| `buyers.py` | `BuyerBatchContract` | `buyer_batch_contracts` | `UUID` | Objeto de asociación `M:N` entre `InternationalBuyer` y `ExportBatch` |
| `buyers.py` | `BuyerApiAuditLog` | `buyer_api_audit_logs` | `BIGSERIAL` | `N:1` con `InternationalBuyer` y `ExportBatch` |

---

## 4. Implementación de Modelos por Módulo

### 4.1 Clase Base y Mixins (`app/models/base.py`)

Define la configuración declarativa de SQLAlchemy 2.0, el mixin de auditoría temporal en UTC (`created_at`, `updated_at`) y la clase `BaseModel` con `UUID` autogenerado en PostgreSQL mediante `gen_random_uuid()`.

```python
import uuid
from datetime import datetime
from sqlalchemy import DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Clase base declarativa para todos los modelos de SQLAlchemy 2.0."""

    pass


class TimestampMixin:
    """Mixin para auditoría automática de creación y actualización en UTC."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class BaseModel(Base, TimestampMixin):
    """
    Clase base abstracta para entidades principales con clave primaria UUID
    y marcas de tiempo de auditoría (created_at, updated_at).
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
```

---

### 4.2 Módulo de Ubicación Geográfica (`app/models/location.py`)

```python
from typing import TYPE_CHECKING, Optional
from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.farm import Farm


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    department_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dane_code: Mapped[str] = mapped_column(String(5), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Relaciones
    municipalities: Mapped[list["Municipality"]] = relationship(
        "Municipality",
        back_populates="department",
        cascade="all, delete-orphan",
    )


class Municipality(Base, TimestampMixin):
    __tablename__ = "municipalities"
    __table_args__ = (
        CheckConstraint(
            "altitude_avg_masl BETWEEN 400 AND 3000",
            name="ck_municipalities_altitude_range",
        ),
        Index("ix_municipalities_dept_name", "department_id", "name"),
    )

    municipality_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.department_id", ondelete="RESTRICT"),
        nullable=False,
    )
    dane_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    altitude_avg_masl: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relaciones
    department: Mapped["Department"] = relationship("Department", back_populates="municipalities")
    farms: Mapped[list["Farm"]] = relationship("Farm", back_populates="municipality")
```

---

### 4.3 Módulo Core & Fincas (`app/models/farm.py`)

```python
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.alerts import AgronomicAlert, AgronomistFieldVisit
    from app.models.iot import IoTSensor
    from app.models.location import Municipality
    from app.models.soil import CropNutrientReference, FertilizerRecommendation, SoilLabAnalysis
    from app.models.traceability import BatchFarmComposition, FarmReserveOverlap


class CoffeeVariety(Base):
    __tablename__ = "coffee_varieties"
    __table_args__ = (
        CheckConstraint(
            "rust_resistance_level IN ('LOW', 'MEDIUM', 'HIGH')",
            name="ck_coffee_varieties_rust_level",
        ),
        CheckConstraint("optimal_temp_min_c >= 10.0", name="ck_coffee_varieties_temp_min"),
        CheckConstraint("optimal_temp_max_c <= 35.0", name="ck_coffee_varieties_temp_max"),
    )

    variety_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    rust_resistance_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="MEDIUM", server_default="MEDIUM"
    )
    optimal_temp_min_c: Mapped[Decimal] = mapped_column(
        Numeric(4, 1), nullable=False, default=Decimal("17.0"), server_default="17.0"
    )
    optimal_temp_max_c: Mapped[Decimal] = mapped_column(
        Numeric(4, 1), nullable=False, default=Decimal("24.0"), server_default="24.0"
    )

    # Relaciones
    plots: Mapped[list["FarmPlot"]] = relationship("FarmPlot", back_populates="variety")
    nutrient_references: Mapped[list["CropNutrientReference"]] = relationship(
        "CropNutrientReference", back_populates="variety"
    )


class Farm(Base, TimestampMixin):
    __tablename__ = "farms"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -4.23 AND 13.50", name="ck_farms_latitude"),
        CheckConstraint("longitude BETWEEN -81.73 AND -66.85", name="ck_farms_longitude"),
        CheckConstraint("altitude_masl BETWEEN 800 AND 2600", name="ck_farms_altitude"),
        CheckConstraint("total_area_ha > 0", name="ck_farms_total_area_positive"),
        Index("ix_farms_coordinates", "latitude", "longitude"),
    )

    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    farm_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    municipality_id: Mapped[int] = mapped_column(
        ForeignKey("municipalities.municipality_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    producer_name: Mapped[str] = mapped_column(String(150), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    altitude_masl: Mapped[int] = mapped_column(Integer, nullable=False)
    total_area_ha: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    is_pilot_sensor_farm: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("FALSE")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("TRUE")
    )

    # Relaciones (1:N y Asociaciones M:N)
    municipality: Mapped["Municipality"] = relationship("Municipality", back_populates="farms")
    plots: Mapped[list["FarmPlot"]] = relationship(
        "FarmPlot", back_populates="farm", cascade="all, delete-orphan"
    )
    sensors: Mapped[list["IoTSensor"]] = relationship(
        "IoTSensor", back_populates="farm", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["AgronomicAlert"]] = relationship(
        "AgronomicAlert", back_populates="farm", cascade="all, delete-orphan"
    )
    field_visits: Mapped[list["AgronomistFieldVisit"]] = relationship(
        "AgronomistFieldVisit", back_populates="farm"
    )
    reserve_overlaps: Mapped[list["FarmReserveOverlap"]] = relationship(
        "FarmReserveOverlap", back_populates="farm", cascade="all, delete-orphan"
    )
    batch_compositions: Mapped[list["BatchFarmComposition"]] = relationship(
        "BatchFarmComposition", back_populates="farm"
    )


class FarmPlot(Base, TimestampMixin):
    __tablename__ = "farm_plots"
    __table_args__ = (
        UniqueConstraint("farm_id", "plot_number", name="uq_farm_plots_farm_number"),
        CheckConstraint("plot_number > 0", name="ck_farm_plots_number_positive"),
        CheckConstraint("cultivated_area_ha > 0", name="ck_farm_plots_area_positive"),
        CheckConstraint(
            "tree_density_per_ha BETWEEN 1000 AND 12000",
            name="ck_farm_plots_tree_density",
        ),
    )

    plot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("farms.farm_id", ondelete="CASCADE"), nullable=False, index=True
    )
    variety_id: Mapped[int] = mapped_column(
        ForeignKey("coffee_varieties.variety_id", ondelete="RESTRICT"), nullable=False
    )
    plot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    cultivated_area_ha: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    tree_density_per_ha: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5000, server_default="5000"
    )
    planting_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Relaciones
    farm: Mapped["Farm"] = relationship("Farm", back_populates="plots")
    variety: Mapped["CoffeeVariety"] = relationship("CoffeeVariety", back_populates="plots")
    sensors: Mapped[list["IoTSensor"]] = relationship("IoTSensor", back_populates="plot")
    soil_analyses: Mapped[list["SoilLabAnalysis"]] = relationship(
        "SoilLabAnalysis", back_populates="plot", cascade="all, delete-orphan"
    )
    fertilizer_recommendations: Mapped[list["FertilizerRecommendation"]] = relationship(
        "FertilizerRecommendation", back_populates="plot", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["AgronomicAlert"]] = relationship("AgronomicAlert", back_populates="plot")
    batch_compositions: Mapped[list["BatchFarmComposition"]] = relationship(
        "BatchFarmComposition", back_populates="plot"
    )
```

---

### 4.4 Módulo IoT & Telemetría (`app/models/iot.py`)

```python
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.farm import Farm, FarmPlot


class IoTSensor(Base, TimestampMixin):
    __tablename__ = "iot_sensors"
    __table_args__ = (
        CheckConstraint(
            "sensor_type IN ('SOIL_MOISTURE', 'TEMPERATURE', 'PLUVIOMETER', 'MULTI_AGRO')",
            name="ck_iot_sensors_type",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'OFFLINE', 'MAINTENANCE', 'RETIRED')",
            name="ck_iot_sensors_status",
        ),
    )

    sensor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    serial_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    farm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("farms.farm_id", ondelete="CASCADE"), nullable=False, index=True
    )
    plot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("farm_plots.plot_id", ondelete="SET NULL"), nullable=True
    )
    sensor_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="MULTI_AGRO", server_default="MULTI_AGRO"
    )
    firmware_version: Mapped[str] = mapped_column(
        String(20), nullable=False, default="v1.0.0", server_default="v1.0.0"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ACTIVE", server_default="ACTIVE"
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    installed_at: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )

    # Relaciones
    farm: Mapped["Farm"] = relationship("Farm", back_populates="sensors")
    plot: Mapped[Optional["FarmPlot"]] = relationship("FarmPlot", back_populates="sensors")
    anomalies: Mapped[list["SensorAnomaliesLog"]] = relationship(
        "SensorAnomaliesLog", back_populates="sensor", cascade="all, delete-orphan"
    )


class SensorAnomaliesLog(Base):
    __tablename__ = "sensor_anomalies_log"
    __table_args__ = (
        CheckConstraint(
            "anomaly_type IN ('OUT_OF_RANGE', 'DUPLICATE_BLOCK', 'STALE_OVER_7_DAYS', 'NULL_PAYLOAD')",
            name="ck_sensor_anomalies_type",
        ),
    )

    anomaly_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sensor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("iot_sensors.sensor_id", ondelete="CASCADE"), nullable=False, index=True
    )
    reading_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    anomaly_type: Mapped[str] = mapped_column(String(40), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Relaciones
    sensor: Mapped["IoTSensor"] = relationship("IoTSensor", back_populates="anomalies")
```

---

### 4.5 Módulo Suelos & Nutrición (`app/models/soil.py`)

```python
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.farm import CoffeeVariety, FarmPlot


class SoilLabAnalysis(Base, TimestampMixin):
    __tablename__ = "soil_lab_analyses"
    __table_args__ = (
        CheckConstraint("ph_level BETWEEN 3.00 AND 9.50", name="ck_soil_analyses_ph_range"),
        CheckConstraint(
            "organic_matter_pct BETWEEN 0.00 AND 100.00",
            name="ck_soil_analyses_organic_matter",
        ),
        CheckConstraint("nitrogen_ppm >= 0", name="ck_soil_analyses_n_positive"),
        CheckConstraint("phosphorus_ppm >= 0", name="ck_soil_analyses_p_positive"),
        CheckConstraint("potassium_cmol_kg >= 0", name="ck_soil_analyses_k_positive"),
        CheckConstraint(
            "soil_texture IN ('SANDY', 'LOAM', 'CLAY_LOAM', 'CLAY', 'SILTY')",
            name="ck_soil_analyses_texture",
        ),
        Index("ix_soil_lab_analyses_plot_sample_date", "plot_id", "sample_date"),
    )

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    plot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("farm_plots.plot_id", ondelete="CASCADE"), nullable=False
    )
    sample_date: Mapped[date] = mapped_column(Date, nullable=False)
    ph_level: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    organic_matter_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    nitrogen_ppm: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    phosphorus_ppm: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    potassium_cmol_kg: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    soil_texture: Mapped[str] = mapped_column(String(30), nullable=False)

    # Relaciones
    plot: Mapped["FarmPlot"] = relationship("FarmPlot", back_populates="soil_analyses")
    recommendations: Mapped[list["FertilizerRecommendation"]] = relationship(
        "FertilizerRecommendation", back_populates="soil_analysis"
    )


class CropNutrientReference(Base):
    __tablename__ = "crop_nutrient_references"
    __table_args__ = (
        UniqueConstraint("variety_id", "growth_stage", name="uq_nutrient_ref_variety_stage"),
        CheckConstraint(
            "growth_stage IN ('VEGETATIVE', 'FLOWERING', 'GRAIN_FILLING', 'POST_HARVEST')",
            name="ck_nutrient_ref_stage",
        ),
        CheckConstraint("target_ph_min >= 4.00", name="ck_nutrient_ref_ph_min"),
        CheckConstraint("target_ph_max <= 7.00", name="ck_nutrient_ref_ph_max"),
        CheckConstraint("req_nitrogen_kg_ha >= 0", name="ck_nutrient_ref_n"),
        CheckConstraint("req_phosphorus_kg_ha >= 0", name="ck_nutrient_ref_p"),
        CheckConstraint("req_potassium_kg_ha >= 0", name="ck_nutrient_ref_k"),
    )

    reference_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    variety_id: Mapped[int] = mapped_column(
        ForeignKey("coffee_varieties.variety_id", ondelete="CASCADE"), nullable=False
    )
    growth_stage: Mapped[str] = mapped_column(String(30), nullable=False)
    target_ph_min: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("5.00"), server_default="5.00"
    )
    target_ph_max: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("5.80"), server_default="5.80"
    )
    req_nitrogen_kg_ha: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    req_phosphorus_kg_ha: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    req_potassium_kg_ha: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)

    # Relaciones
    variety: Mapped["CoffeeVariety"] = relationship(
        "CoffeeVariety", back_populates="nutrient_references"
    )


class FertilizerRecommendation(Base, TimestampMixin):
    __tablename__ = "fertilizer_recommendations"
    __table_args__ = (
        CheckConstraint("recommended_n_kg_ha >= 0", name="ck_fert_rec_n_positive"),
        CheckConstraint("recommended_p_kg_ha >= 0", name="ck_fert_rec_p_positive"),
        CheckConstraint("recommended_k_kg_ha >= 0", name="ck_fert_rec_k_positive"),
        CheckConstraint("lime_amendment_kg_ha >= 0", name="ck_fert_rec_lime_positive"),
        CheckConstraint(
            "estimated_saving_pct BETWEEN -100.00 AND 100.00",
            name="ck_fert_rec_saving_pct",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'APPLIED', 'EXPIRED')",
            name="ck_fert_rec_status",
        ),
    )

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    plot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("farm_plots.plot_id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("soil_lab_analyses.analysis_id", ondelete="RESTRICT"), nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    recommended_n_kg_ha: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    recommended_p_kg_ha: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    recommended_k_kg_ha: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    lime_amendment_kg_ha: Mapped[Decimal] = mapped_column(
        Numeric(7, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    estimated_saving_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", server_default="PENDING"
    )

    # Relaciones
    plot: Mapped["FarmPlot"] = relationship("FarmPlot", back_populates="fertilizer_recommendations")
    soil_analysis: Mapped["SoilLabAnalysis"] = relationship(
        "SoilLabAnalysis", back_populates="recommendations"
    )
```

---

### 4.6 Módulo Alertas & Visitas (`app/models/alerts.py`)

```python
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.farm import Farm, FarmPlot


class AgronomicAlert(Base, TimestampMixin):
    __tablename__ = "agronomic_alerts"
    __table_args__ = (
        CheckConstraint(
            "alert_type IN ('COFFEE_RUST', 'WATER_DEFICIT', 'EXTREME_RAIN', 'SOIL_ACIDITY')",
            name="ck_agronomic_alerts_type",
        ),
        CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_agronomic_alerts_severity",
        ),
        CheckConstraint(
            "status IN ('OPEN', 'ASSIGNED', 'RESOLVED', 'DISMISSED')",
            name="ck_agronomic_alerts_status",
        ),
        Index("ix_agronomic_alerts_dashboard", "status", "severity", "generated_at"),
    )

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("farms.farm_id", ondelete="CASCADE"), nullable=False, index=True
    )
    plot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("farm_plots.plot_id", ondelete="SET NULL"), nullable=True
    )
    rule_code: Mapped[str] = mapped_column(String(15), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(15), nullable=False)
    forecast_target_date: Mapped[date] = mapped_column(Date, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_reprocessed_late_data: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("FALSE")
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="OPEN", server_default="OPEN"
    )

    # Relaciones
    farm: Mapped["Farm"] = relationship("Farm", back_populates="alerts")
    plot: Mapped[Optional["FarmPlot"]] = relationship("FarmPlot", back_populates="alerts")
    field_visits: Mapped[list["AgronomistFieldVisit"]] = relationship(
        "AgronomistFieldVisit", back_populates="alert"
    )


class AgronomistFieldVisit(Base, TimestampMixin):
    __tablename__ = "agronomist_field_visits"
    __table_args__ = (
        CheckConstraint(
            "rust_incidence_pct BETWEEN 0.00 AND 100.00",
            name="ck_field_visits_rust_pct",
        ),
        CheckConstraint(
            "visit_outcome IN ('SCHEDULED', 'COMPLETED_OK', 'TREATMENT_APPLIED', 'FALSE_ALARM')",
            name="ck_field_visits_outcome",
        ),
    )

    visit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    alert_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("agronomic_alerts.alert_id", ondelete="SET NULL"), nullable=True, index=True
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("farms.farm_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    agronomist_name: Mapped[str] = mapped_column(String(120), nullable=False)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rust_incidence_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    visit_outcome: Mapped[str] = mapped_column(
        String(30), nullable=False, default="SCHEDULED", server_default="SCHEDULED"
    )
    field_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relaciones
    alert: Mapped[Optional["AgronomicAlert"]] = relationship(
        "AgronomicAlert", back_populates="field_visits"
    )
    farm: Mapped["Farm"] = relationship("Farm", back_populates="field_visits")
```

---

### 4.7 Módulo Trazabilidad & Reserva Forestal (`app/models/traceability.py`)

```python
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.buyers import BuyerApiAuditLog, BuyerBatchContract
    from app.models.farm import Farm, FarmPlot


class ForestReserve(Base, TimestampMixin):
    __tablename__ = "forest_reserves"

    reserve_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    official_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    protection_category: Mapped[str] = mapped_column(String(50), nullable=False)
    boundary_geojson: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Relaciones
    farm_overlaps: Mapped[list["FarmReserveOverlap"]] = relationship(
        "FarmReserveOverlap", back_populates="reserve"
    )


class FarmReserveOverlap(Base):
    """Modelo de asociación espacial (M:N) entre Farm y ForestReserve."""

    __tablename__ = "farm_reserve_overlaps"
    __table_args__ = (
        CheckConstraint("overlap_area_ha >= 0", name="ck_farm_reserve_overlap_area"),
        CheckConstraint(
            "deforestation_free_status IN ('COMPLIANT', 'BUFFER_ZONE_WARNING', 'NON_COMPLIANT')",
            name="ck_farm_reserve_deforestation_status",
        ),
    )

    overlap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("farms.farm_id", ondelete="CASCADE"), nullable=False, index=True
    )
    reserve_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("forest_reserves.reserve_id", ondelete="SET NULL"), nullable=True
    )
    overlap_area_ha: Mapped[Decimal] = mapped_column(
        Numeric(8, 3), nullable=False, default=Decimal("0.000"), server_default="0.000"
    )
    deforestation_free_status: Mapped[str] = mapped_column(
        String(25), nullable=False, default="COMPLIANT", server_default="COMPLIANT"
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relaciones
    farm: Mapped["Farm"] = relationship("Farm", back_populates="reserve_overlaps")
    reserve: Mapped[Optional["ForestReserve"]] = relationship(
        "ForestReserve", back_populates="farm_overlaps"
    )


class ExportBatch(Base, TimestampMixin):
    __tablename__ = "export_batches"
    __table_args__ = (
        CheckConstraint("total_weight_kg > 0", name="ck_export_batches_weight_positive"),
        CheckConstraint(
            "cupping_score BETWEEN 80.00 AND 100.00",
            name="ck_export_batches_cupping_score",
        ),
        CheckConstraint("water_footprint_l_per_kg >= 0", name="ck_export_batches_water_positive"),
        CheckConstraint(
            "is_deforestation_free = TRUE", name="ck_export_batches_deforestation_free"
        ),
        CheckConstraint(
            "traceability_status IN ('DRAFT', 'CERTIFIED', 'EXPORTED', 'REJECTED')",
            name="ck_export_batches_status",
        ),
    )

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    batch_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    harvest_season: Mapped[str] = mapped_column(String(20), nullable=False)
    total_weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cupping_score: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    water_footprint_l_per_kg: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    fertilizer_reduction_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    is_deforestation_free: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("TRUE")
    )
    traceability_status: Mapped[str] = mapped_column(
        String(25), nullable=False, default="CERTIFIED", server_default="CERTIFIED"
    )
    certified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relaciones
    farm_compositions: Mapped[list["BatchFarmComposition"]] = relationship(
        "BatchFarmComposition", back_populates="batch", cascade="all, delete-orphan"
    )
    buyer_contracts: Mapped[list["BuyerBatchContract"]] = relationship(
        "BuyerBatchContract", back_populates="batch", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["BuyerApiAuditLog"]] = relationship(
        "BuyerApiAuditLog", back_populates="batch"
    )


class BatchFarmComposition(Base):
    """Modelo de asociación (M:N) que desglosa el aporte de cada Finca/Lote a un ExportBatch."""

    __tablename__ = "batch_farm_compositions"
    __table_args__ = (
        UniqueConstraint("batch_id", "plot_id", name="uq_batch_composition_batch_plot"),
        CheckConstraint("contributed_weight_kg > 0", name="ck_batch_comp_weight_positive"),
        CheckConstraint(
            "contribution_pct > 0 AND contribution_pct <= 100.00",
            name="ck_batch_comp_pct_range",
        ),
    )

    composition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("export_batches.batch_id", ondelete="CASCADE"), nullable=False, index=True
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("farms.farm_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    plot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("farm_plots.plot_id", ondelete="RESTRICT"), nullable=False
    )
    contributed_weight_kg: Mapped[Decimal] = mapped_column(Numeric(9, 2), nullable=False)
    contribution_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    reception_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Relaciones
    batch: Mapped["ExportBatch"] = relationship("ExportBatch", back_populates="farm_compositions")
    farm: Mapped["Farm"] = relationship("Farm", back_populates="batch_compositions")
    plot: Mapped["FarmPlot"] = relationship("FarmPlot", back_populates="batch_compositions")
```

---

### 4.8 Módulo Compradores & Seguridad API (`app/models/buyers.py`)

```python
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.traceability import ExportBatch


class InternationalBuyer(Base, TimestampMixin):
    __tablename__ = "international_buyers"
    __table_args__ = (
        CheckConstraint(
            "rate_limit_per_min BETWEEN 10 AND 1000",
            name="ck_buyers_rate_limit_range",
        ),
    )

    buyer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    company_name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    country_iso_code: Mapped[str] = mapped_column(CHAR(2), nullable=False)
    api_client_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    api_key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    rate_limit_per_min: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60, server_default="60"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("TRUE")
    )

    # Relaciones
    batch_contracts: Mapped[list["BuyerBatchContract"]] = relationship(
        "BuyerBatchContract", back_populates="buyer", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["BuyerApiAuditLog"]] = relationship(
        "BuyerApiAuditLog", back_populates="buyer"
    )


class BuyerBatchContract(Base):
    """Modelo de asociación (M:N) que aísla qué lotes puede consultar cada comprador (RNF-06)."""

    __tablename__ = "buyer_batch_contracts"
    __table_args__ = (UniqueConstraint("buyer_id", "batch_id", name="uq_buyer_batch_contract"),)

    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("international_buyers.buyer_id", ondelete="CASCADE"), nullable=False, index=True
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("export_batches.batch_id", ondelete="CASCADE"), nullable=False, index=True
    )
    contract_reference: Mapped[str] = mapped_column(String(50), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relaciones
    buyer: Mapped["InternationalBuyer"] = relationship(
        "InternationalBuyer", back_populates="batch_contracts"
    )
    batch: Mapped["ExportBatch"] = relationship("ExportBatch", back_populates="buyer_contracts")


class BuyerApiAuditLog(Base):
    __tablename__ = "buyer_api_audit_logs"
    __table_args__ = (
        CheckConstraint("http_status_code BETWEEN 100 AND 599", name="ck_api_audit_http_status"),
        CheckConstraint("response_time_ms >= 0", name="ck_api_audit_response_time"),
    )

    log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("international_buyers.buyer_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("export_batches.batch_id", ondelete="SET NULL"), nullable=True
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    http_status_code: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=200, server_default="200"
    )
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    client_ip: Mapped[str] = mapped_column(String(45), nullable=False)

    # Relaciones
    buyer: Mapped["InternationalBuyer"] = relationship(
        "InternationalBuyer", back_populates="audit_logs"
    )
    batch: Mapped[Optional["ExportBatch"]] = relationship(
        "ExportBatch", back_populates="audit_logs"
    )
```

---

### 4.9 Registro Central para Alembic (`app/models/__init__.py`)

Para que `alembic revision --autogenerate` detecte todas las tablas y relaciones, el archivo `app/models/__init__.py` debe exponer `Base` e importar todos los modelos:

```python
from app.models.alerts import AgronomicAlert, AgronomistFieldVisit
from app.models.base import Base, BaseModel, TimestampMixin
from app.models.buyers import BuyerApiAuditLog, BuyerBatchContract, InternationalBuyer
from app.models.farm import CoffeeVariety, Farm, FarmPlot
from app.models.iot import IoTSensor, SensorAnomaliesLog
from app.models.location import Department, Municipality
from app.models.soil import CropNutrientReference, FertilizerRecommendation, SoilLabAnalysis
from app.models.traceability import (
    BatchFarmComposition,
    ExportBatch,
    FarmReserveOverlap,
    ForestReserve,
)

__all__ = [
    "Base",
    "BaseModel",
    "TimestampMixin",
    "Department",
    "Municipality",
    "CoffeeVariety",
    "Farm",
    "FarmPlot",
    "IoTSensor",
    "SensorAnomaliesLog",
    "SoilLabAnalysis",
    "CropNutrientReference",
    "FertilizerRecommendation",
    "AgronomicAlert",
    "AgronomistFieldVisit",
    "ForestReserve",
    "FarmReserveOverlap",
    "ExportBatch",
    "BatchFarmComposition",
    "InternationalBuyer",
    "BuyerBatchContract",
    "BuyerApiAuditLog",
]
```
