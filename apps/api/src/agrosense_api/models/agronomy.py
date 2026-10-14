from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .farm import Farm, FarmPlot
    from .soil_lab_analysis import SoilLabAnalysis


class FertilizerRecommendation(BaseModel):
    """Recomendación RN-07 asociada de forma única a un análisis F6."""

    __tablename__ = "fertilizer_recommendations"
    __table_args__ = (
        CheckConstraint(
            "recommended_n_kg_ha >= 0 AND recommended_p_kg_ha >= 0 "
            "AND recommended_k_kg_ha >= 0 AND lime_amendment_kg_ha >= 0",
            name="nonnegative_doses",
        ),
        CheckConstraint(
            "estimated_saving_pct BETWEEN 0 AND 100",
            name="saving_range",
        ),
        CheckConstraint(
            "n_evaluation IN ('DEFICIENT', 'OPTIMAL', 'EXCESS_WARNING')",
            name="n_evaluation",
        ),
        CheckConstraint(
            "p_evaluation IN ('DEFICIENT', 'OPTIMAL', 'EXCESS_WARNING')",
            name="p_evaluation",
        ),
        CheckConstraint(
            "k_evaluation IN ('DEFICIENT', 'OPTIMAL', 'EXCESS_WARNING')",
            name="k_evaluation",
        ),
        CheckConstraint(
            "ph_evaluation IN ('ACIDIC', 'OPTIMAL', 'ALKALINE')",
            name="ph_evaluation",
        ),
    )

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "soil_lab_analyses.analysis_id",
            ondelete="CASCADE",
            name="fk_fertilizer_recommendations_analysis_id",
        ),
        nullable=False,
        unique=True,
        index=True,
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "farms.farm_id",
            ondelete="CASCADE",
            name="fk_fertilizer_recommendations_farm_id",
        ),
        nullable=False,
        index=True,
    )
    plot_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "farm_plots.plot_id",
            ondelete="CASCADE",
            name="fk_fertilizer_recommendations_plot_id",
        ),
        nullable=False,
        index=True,
    )
    n_evaluation: Mapped[str] = mapped_column(String(20), nullable=False)
    p_evaluation: Mapped[str] = mapped_column(String(20), nullable=False)
    k_evaluation: Mapped[str] = mapped_column(String(20), nullable=False)
    ph_evaluation: Mapped[str] = mapped_column(String(20), nullable=False)
    apply_fertilizer: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recommended_n_kg_ha: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    recommended_p_kg_ha: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    recommended_k_kg_ha: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    lime_amendment_kg_ha: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, default=Decimal("0")
    )
    estimated_saving_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    warning_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="GENERATED", server_default="GENERATED"
    )

    analysis: Mapped[SoilLabAnalysis] = relationship(
        "SoilLabAnalysis", back_populates="fertilizer_recommendation"
    )
    farm: Mapped[Farm] = relationship("Farm")
    plot: Mapped[FarmPlot] = relationship("FarmPlot", back_populates="fertilizer_recommendations")


class AgronomicAlert(BaseModel):
    """Alerta determinista de roya, déficit hídrico o lluvia extrema."""

    __tablename__ = "agronomic_alerts"
    __table_args__ = (
        CheckConstraint(
            "alert_type IN ('COFFEE_RUST', 'WATER_DEFICIT', 'EXTREME_RAIN')",
            name="alert_type",
        ),
        CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="severity",
        ),
        CheckConstraint(
            "status IN ('OPEN', 'ASSIGNED', 'RESOLVED', 'DISMISSED')",
            name="status",
        ),
    )

    alert_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("farms.farm_id", ondelete="CASCADE", name="fk_agronomic_alerts_farm_id"),
        nullable=False,
        index=True,
    )
    plot_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("farm_plots.plot_id", ondelete="SET NULL", name="fk_agronomic_alerts_plot_id"),
        nullable=True,
        index=True,
    )
    rule_code: Mapped[str] = mapped_column(String(15), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(15), nullable=False)
    forecast_target_date: Mapped[date] = mapped_column(Date, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="OPEN", server_default="OPEN"
    )

    farm: Mapped[Farm] = relationship("Farm", back_populates="agronomic_alerts")
    plot: Mapped[FarmPlot | None] = relationship("FarmPlot", back_populates="agronomic_alerts")
