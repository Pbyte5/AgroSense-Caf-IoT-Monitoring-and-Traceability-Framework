"""Add soil references, recommendations, and agronomic alerts for AGRO-08.

Revision ID: 4a7c19e2b6d1
Revises: 927ccb53d091
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "4a7c19e2b6d1"
down_revision = "927ccb53d091"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "farm_plots",
        sa.Column(
            "growth_stage",
            sa.String(length=50),
            server_default=sa.text("'VEGETATIVE'"),
            nullable=False,
        ),
    )

    op.create_table(
        "crop_nutrient_references",
        sa.Column("reference_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("variety_id", sa.Integer(), nullable=False),
        sa.Column("crop_label", sa.String(length=100), nullable=False),
        sa.Column("growth_stage", sa.String(length=50), nullable=False),
        sa.Column("target_ph_min", sa.Float(), nullable=False),
        sa.Column("target_ph_max", sa.Float(), nullable=False),
        sa.Column("ph_min", sa.Float(), nullable=False),
        sa.Column("ph_max", sa.Float(), nullable=False),
        sa.Column("req_nitrogen_kg_ha", sa.Numeric(8, 2), nullable=False),
        sa.Column("n_min_mg_kg", sa.Numeric(8, 2), nullable=False),
        sa.Column("n_max_mg_kg", sa.Numeric(8, 2), nullable=False),
        sa.Column("req_phosphorus_kg_ha", sa.Numeric(8, 2), nullable=False),
        sa.Column("p_min_mg_kg", sa.Numeric(8, 2), nullable=False),
        sa.Column("p_max_mg_kg", sa.Numeric(8, 2), nullable=False),
        sa.Column("req_potassium_kg_ha", sa.Numeric(8, 2), nullable=False),
        sa.Column("k_min_mg_kg", sa.Numeric(8, 2), nullable=False),
        sa.Column("k_max_mg_kg", sa.Numeric(8, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["variety_id"],
            ["coffee_varieties.variety_id"],
            name="fk_crop_nutrient_references_variety_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("reference_id", name=op.f("pk_crop_nutrient_references")),
        sa.UniqueConstraint(
            "variety_id",
            "growth_stage",
            name="uq_crop_nutrient_references_variety_stage",
        ),
    )
    op.create_index(
        op.f("ix_crop_nutrient_references_variety_id"),
        "crop_nutrient_references",
        ["variety_id"],
        unique=False,
    )

    op.create_table(
        "soil_lab_analyses",
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sample_date", sa.Date(), nullable=False),
        sa.Column("raw_unit_reported", sa.String(length=30), nullable=False),
        sa.Column("ph_level", sa.Numeric(5, 2), nullable=False),
        sa.Column("ph_value", sa.Numeric(5, 2), nullable=False),
        sa.Column("organic_matter_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("nitrogen_ppm", sa.Numeric(8, 2), nullable=False),
        sa.Column("nitrogen_mg_kg", sa.Numeric(8, 2), nullable=False),
        sa.Column("phosphorus_ppm", sa.Numeric(8, 2), nullable=False),
        sa.Column("phosphorus_mg_kg", sa.Numeric(8, 2), nullable=False),
        sa.Column("potassium_cmol_kg", sa.Numeric(8, 3), nullable=False),
        sa.Column("potassium_mg_kg", sa.Numeric(8, 2), nullable=False),
        sa.Column("soil_texture", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_soil_lab_analyses_farm_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plot_id"],
            ["farm_plots.plot_id"],
            name="fk_soil_lab_analyses_plot_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("analysis_id", name=op.f("pk_soil_lab_analyses")),
    )
    op.create_index(
        op.f("ix_soil_lab_analyses_farm_id"),
        "soil_lab_analyses",
        ["farm_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_soil_lab_analyses_plot_id"),
        "soil_lab_analyses",
        ["plot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_soil_lab_analyses_sample_date"),
        "soil_lab_analyses",
        ["sample_date"],
        unique=False,
    )

    op.create_table(
        "fertilizer_recommendations",
        sa.Column(
            "recommendation_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("n_evaluation", sa.String(length=20), nullable=False),
        sa.Column("p_evaluation", sa.String(length=20), nullable=False),
        sa.Column("k_evaluation", sa.String(length=20), nullable=False),
        sa.Column("ph_evaluation", sa.String(length=20), nullable=False),
        sa.Column("apply_fertilizer", sa.Boolean(), nullable=False),
        sa.Column("recommended_n_kg_ha", sa.Numeric(6, 2), nullable=False),
        sa.Column("recommended_p_kg_ha", sa.Numeric(6, 2), nullable=False),
        sa.Column("recommended_k_kg_ha", sa.Numeric(6, 2), nullable=False),
        sa.Column(
            "lime_amendment_kg_ha",
            sa.Numeric(6, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("estimated_saving_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("warning_message", sa.String(length=500), nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default=sa.text("'GENERATED'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "recommended_n_kg_ha >= 0 AND recommended_p_kg_ha >= 0 "
            "AND recommended_k_kg_ha >= 0 AND lime_amendment_kg_ha >= 0",
            name="nonnegative_doses",
        ),
        sa.CheckConstraint(
            "estimated_saving_pct BETWEEN 0 AND 100",
            name="saving_range",
        ),
        sa.CheckConstraint(
            "n_evaluation IN ('DEFICIENT', 'OPTIMAL', 'EXCESS_WARNING')",
            name="n_evaluation",
        ),
        sa.CheckConstraint(
            "p_evaluation IN ('DEFICIENT', 'OPTIMAL', 'EXCESS_WARNING')",
            name="p_evaluation",
        ),
        sa.CheckConstraint(
            "k_evaluation IN ('DEFICIENT', 'OPTIMAL', 'EXCESS_WARNING')",
            name="k_evaluation",
        ),
        sa.CheckConstraint(
            "ph_evaluation IN ('ACIDIC', 'OPTIMAL', 'ALKALINE')",
            name="ph_evaluation",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["soil_lab_analyses.analysis_id"],
            name="fk_fertilizer_recommendations_analysis_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_fertilizer_recommendations_farm_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plot_id"],
            ["farm_plots.plot_id"],
            name="fk_fertilizer_recommendations_plot_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("recommendation_id", name=op.f("pk_fertilizer_recommendations")),
    )
    op.create_index(
        op.f("ix_fertilizer_recommendations_analysis_id"),
        "fertilizer_recommendations",
        ["analysis_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_fertilizer_recommendations_plot_id"),
        "fertilizer_recommendations",
        ["plot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fertilizer_recommendations_farm_id"),
        "fertilizer_recommendations",
        ["farm_id"],
        unique=False,
    )

    op.create_table(
        "agronomic_alerts",
        sa.Column(
            "alert_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rule_code", sa.String(length=15), nullable=False),
        sa.Column("alert_type", sa.String(length=30), nullable=False),
        sa.Column("severity", sa.String(length=15), nullable=False),
        sa.Column("forecast_target_date", sa.Date(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'OPEN'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "alert_type IN ('COFFEE_RUST', 'WATER_DEFICIT', 'EXTREME_RAIN')",
            name="alert_type",
        ),
        sa.CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="severity",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'ASSIGNED', 'RESOLVED', 'DISMISSED')",
            name="status",
        ),
        sa.ForeignKeyConstraint(
            ["farm_id"],
            ["farms.farm_id"],
            name="fk_agronomic_alerts_farm_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plot_id"],
            ["farm_plots.plot_id"],
            name="fk_agronomic_alerts_plot_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("alert_id", name=op.f("pk_agronomic_alerts")),
    )
    op.create_index(
        op.f("ix_agronomic_alerts_farm_id"),
        "agronomic_alerts",
        ["farm_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agronomic_alerts_plot_id"),
        "agronomic_alerts",
        ["plot_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_agronomic_alerts_plot_id"), table_name="agronomic_alerts")
    op.drop_index(op.f("ix_agronomic_alerts_farm_id"), table_name="agronomic_alerts")
    op.drop_table("agronomic_alerts")
    op.drop_index(
        op.f("ix_fertilizer_recommendations_farm_id"),
        table_name="fertilizer_recommendations",
    )
    op.drop_index(
        op.f("ix_fertilizer_recommendations_plot_id"),
        table_name="fertilizer_recommendations",
    )
    op.drop_index(
        op.f("ix_fertilizer_recommendations_analysis_id"),
        table_name="fertilizer_recommendations",
    )
    op.drop_table("fertilizer_recommendations")
    op.drop_index(op.f("ix_soil_lab_analyses_sample_date"), table_name="soil_lab_analyses")
    op.drop_index(op.f("ix_soil_lab_analyses_plot_id"), table_name="soil_lab_analyses")
    op.drop_index(op.f("ix_soil_lab_analyses_farm_id"), table_name="soil_lab_analyses")
    op.drop_table("soil_lab_analyses")
    op.drop_index(
        op.f("ix_crop_nutrient_references_variety_id"),
        table_name="crop_nutrient_references",
    )
    op.drop_table("crop_nutrient_references")
    op.drop_column("farm_plots", "growth_stage")
