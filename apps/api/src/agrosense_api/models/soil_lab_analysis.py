from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .agronomy import FertilizerRecommendation
    from .farm import Farm, FarmPlot


class SoilLabAnalysis(BaseModel):
    """Análisis F6 de laboratorio, conservando valores reportados y normalizados."""

    __tablename__ = "soil_lab_analyses"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("farms.farm_id", ondelete="CASCADE", name="fk_soil_lab_analyses_farm_id"),
        nullable=False,
        index=True,
    )
    plot_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "farm_plots.plot_id",
            ondelete="CASCADE",
            name="fk_soil_lab_analyses_plot_id",
        ),
        nullable=False,
        index=True,
    )
    sample_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    raw_unit_reported: Mapped[str] = mapped_column(String(30), nullable=False)
    ph_level: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    ph_value: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    organic_matter_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    nitrogen_ppm: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    nitrogen_mg_kg: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    phosphorus_ppm: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    phosphorus_mg_kg: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    potassium_cmol_kg: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    potassium_mg_kg: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    soil_texture: Mapped[str] = mapped_column(String(50), nullable=False)

    farm: Mapped[Farm] = relationship("Farm")
    plot: Mapped[FarmPlot] = relationship("FarmPlot", back_populates="soil_lab_analyses")
    fertilizer_recommendation: Mapped[FertilizerRecommendation | None] = relationship(
        "FertilizerRecommendation", back_populates="analysis", uselist=False
    )
