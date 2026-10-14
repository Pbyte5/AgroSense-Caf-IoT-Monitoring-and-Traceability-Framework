from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .farm import CoffeeVariety


class CropNutrientReference(BaseModel):
    """Referencia F1 de pH y nutrientes por variedad y etapa fenológica."""

    __tablename__ = "crop_nutrient_references"
    __table_args__ = (
        UniqueConstraint(
            "variety_id",
            "growth_stage",
            name="uq_crop_nutrient_references_variety_stage",
        ),
    )

    reference_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    variety_id: Mapped[int] = mapped_column(
        ForeignKey(
            "coffee_varieties.variety_id",
            ondelete="CASCADE",
            name="fk_crop_nutrient_references_variety_id",
        ),
        nullable=False,
        index=True,
    )
    crop_label: Mapped[str] = mapped_column(String(100), nullable=False)
    growth_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    target_ph_min: Mapped[float] = mapped_column(Float, nullable=False)
    target_ph_max: Mapped[float] = mapped_column(Float, nullable=False)
    ph_min: Mapped[float] = mapped_column(Float, nullable=False)
    ph_max: Mapped[float] = mapped_column(Float, nullable=False)
    req_nitrogen_kg_ha: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    n_min_mg_kg: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    n_max_mg_kg: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    req_phosphorus_kg_ha: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    p_min_mg_kg: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    p_max_mg_kg: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    req_potassium_kg_ha: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    k_min_mg_kg: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    k_max_mg_kg: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)

    variety: Mapped[CoffeeVariety] = relationship(
        "CoffeeVariety", back_populates="nutrient_references"
    )
