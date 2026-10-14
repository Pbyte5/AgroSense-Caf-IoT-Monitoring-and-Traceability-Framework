from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .agronomy import AgronomicAlert, FertilizerRecommendation
    from .batch import BatchFarmComposition
    from .crop_nutrient_reference import CropNutrientReference
    from .harvest import HarvestDelivery
    from .location import Municipality
    from .producer import Producer
    from .soil_lab_analysis import SoilLabAnalysis


class CoffeeVariety(BaseModel):
    """Catálogo de variedades de café cultivadas en las parcelas."""

    __tablename__ = "coffee_varieties"

    variety_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    variety_name: Mapped[str] = mapped_column(
        String(80),
        unique=True,
        nullable=False,
    )

    # Relaciones
    plots: Mapped[list[FarmPlot]] = relationship(
        "FarmPlot",
        back_populates="variety",
    )
    nutrient_references: Mapped[list[CropNutrientReference]] = relationship(
        "CropNutrientReference", back_populates="variety"
    )

    def __repr__(self) -> str:
        return f"<CoffeeVariety(variety_id={self.variety_id}, variety_name='{self.variety_name}')>"


class Farm(BaseModel):
    """Entidad principal de finca cafetera e indicadores agroambientales."""

    __tablename__ = "farms"

    farm_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    farm_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    producer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("producers.producer_id", name="fk_farms_producer_id"),
        nullable=False,
    )
    municipality_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("municipalities.municipality_id", name="fk_farms_municipality_id"),
        nullable=False,
    )
    latitude: Mapped[Decimal] = mapped_column(
        Numeric(9, 6),
        nullable=False,
    )
    longitude: Mapped[Decimal] = mapped_column(
        Numeric(9, 6),
        nullable=False,
    )
    cultivated_area_ha: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        nullable=False,
    )
    water_usage_m3_ton: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )
    overlaps_reserve: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    # Relaciones
    producer: Mapped[Producer] = relationship(
        "Producer",
        back_populates="farms",
    )
    municipality: Mapped[Municipality] = relationship(
        "Municipality",
        back_populates="farms",
    )
    plots: Mapped[list[FarmPlot]] = relationship(
        "FarmPlot",
        back_populates="farm",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    reserve_overlaps: Mapped[list[FarmReserveOverlap]] = relationship(
        "FarmReserveOverlap",
        back_populates="farm",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    harvest_deliveries: Mapped[list[HarvestDelivery]] = relationship(
        "HarvestDelivery",
        back_populates="farm",
    )
    batch_compositions: Mapped[list[BatchFarmComposition]] = relationship(
        "BatchFarmComposition",
        back_populates="farm",
    )
    agronomic_alerts: Mapped[list[AgronomicAlert]] = relationship(
        "AgronomicAlert", back_populates="farm"
    )

    def __repr__(self) -> str:
        return f"<Farm(farm_id={self.farm_id}, farm_code='{self.farm_code}')>"


class FarmReserveOverlap(BaseModel):
    """
    Registro de intersección espacial con reservas forestales (RN-09).
    Almacena el polígono de superposición en EPSG:4326 (WGS84).
    """

    __tablename__ = "farm_reserve_overlaps"

    overlap_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "farms.farm_id",
            ondelete="CASCADE",
            name="fk_farm_reserve_overlaps_farm_id",
        ),
        nullable=False,
    )
    reserve_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    overlap_geometry: Mapped[WKBElement] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326),
        nullable=False,
    )

    # Relaciones
    farm: Mapped[Farm] = relationship(
        "Farm",
        back_populates="reserve_overlaps",
    )

    def __repr__(self) -> str:
        return (
            f"<FarmReserveOverlap(overlap_id={self.overlap_id}, "
            f"reserve_name='{self.reserve_name}')>"
        )


class FarmPlot(BaseModel):
    """Parcela o lote interno de cultivo dentro de una finca."""

    __tablename__ = "farm_plots"

    plot_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "farms.farm_id",
            ondelete="CASCADE",
            name="fk_farm_plots_farm_id",
        ),
        nullable=False,
    )
    variety_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "coffee_varieties.variety_id",
            name="fk_farm_plots_variety_id",
        ),
        nullable=False,
    )
    plot_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    crop_age_years: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    growth_stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="VEGETATIVE",
        server_default=text("'VEGETATIVE'"),
    )

    # Relaciones
    farm: Mapped[Farm] = relationship(
        "Farm",
        back_populates="plots",
    )
    variety: Mapped[CoffeeVariety] = relationship(
        "CoffeeVariety",
        back_populates="plots",
    )
    harvest_deliveries: Mapped[list[HarvestDelivery]] = relationship(
        "HarvestDelivery",
        back_populates="plot",
    )
    soil_lab_analyses: Mapped[list[SoilLabAnalysis]] = relationship(
        "SoilLabAnalysis", back_populates="plot", cascade="all, delete-orphan"
    )
    fertilizer_recommendations: Mapped[list[FertilizerRecommendation]] = relationship(
        "FertilizerRecommendation", back_populates="plot", cascade="all, delete-orphan"
    )
    agronomic_alerts: Mapped[list[AgronomicAlert]] = relationship(
        "AgronomicAlert", back_populates="plot"
    )

    def __repr__(self) -> str:
        return f"<FarmPlot(plot_id={self.plot_id}, plot_name='{self.plot_name}')>"
