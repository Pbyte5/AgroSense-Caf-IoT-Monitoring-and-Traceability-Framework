from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

DATABASE_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "users": ("user_id", "full_name", "role"),
    "producers": (
        "producer_id",
        "document_number",
        "full_name",
        "phone_number",
        "cooperative_join_date",
    ),
    "international_buyers": ("buyer_id", "client_id", "buyer_name"),
    "coffee_varieties": ("variety_id", "variety_name"),
    "crop_nutrient_references": (
        "reference_id",
        "variety_id",
        "crop_label",
        "growth_stage",
        "target_ph_min",
        "target_ph_max",
        "ph_min",
        "ph_max",
        "req_nitrogen_kg_ha",
        "n_min_mg_kg",
        "n_max_mg_kg",
        "req_phosphorus_kg_ha",
        "p_min_mg_kg",
        "p_max_mg_kg",
        "req_potassium_kg_ha",
        "k_min_mg_kg",
        "k_max_mg_kg",
    ),
    "municipalities": ("municipality_id", "name"),
    "farms": (
        "farm_id",
        "farm_code",
        "producer_id",
        "municipality_id",
        "latitude",
        "longitude",
        "cultivated_area_ha",
        "water_usage_m3_ton",
        "overlaps_reserve",
    ),
    "farm_plots": (
        "plot_id",
        "farm_id",
        "variety_id",
        "plot_name",
        "crop_age_years",
        "growth_stage",
    ),
    "soil_lab_analyses": (
        "analysis_id",
        "farm_id",
        "plot_id",
        "sample_date",
        "raw_unit_reported",
        "ph_level",
        "ph_value",
        "organic_matter_pct",
        "nitrogen_ppm",
        "nitrogen_mg_kg",
        "phosphorus_ppm",
        "phosphorus_mg_kg",
        "potassium_cmol_kg",
        "potassium_mg_kg",
        "soil_texture",
    ),
    "fertilizer_recommendations": (
        "recommendation_id",
        "analysis_id",
        "farm_id",
        "plot_id",
        "n_evaluation",
        "p_evaluation",
        "k_evaluation",
        "ph_evaluation",
        "apply_fertilizer",
        "recommended_n_kg_ha",
        "recommended_p_kg_ha",
        "recommended_k_kg_ha",
        "lime_amendment_kg_ha",
        "estimated_saving_pct",
        "warning_message",
        "status",
    ),
    "harvest_deliveries": (
        "delivery_id",
        "farm_id",
        "plot_id",
        "delivery_date",
        "delivered_weight_kg",
    ),
    "export_batches": (
        "batch_id",
        "batch_code",
        "total_weight_kg",
        "traced_weight_kg",
        "is_exportable",
        "is_certified",
        "weighted_water_m3_ton",
    ),
    "batch_farm_compositions": (
        "composition_id",
        "batch_id",
        "delivery_id",
        "farm_id",
        "contributed_kg",
        "share_percentage",
    ),
    "buyer_batch_contracts": ("contract_id", "batch_id", "buyer_id"),
    "agronomic_alerts": (
        "alert_id",
        "farm_id",
        "plot_id",
        "rule_code",
        "alert_type",
        "severity",
        "forecast_target_date",
        "status",
    ),
}


def _project(
    records: Sequence[Mapping[str, Any]],
    columns: tuple[str, ...],
    *,
    aliases: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    aliases = aliases or {}
    projected = []
    for record in records:
        projected.append({column: record[aliases.get(column, column)] for column in columns})
    return projected


def build_database_dataset(
    generated: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Project synthetic records onto the tables in the current API migrations.

    Departments, reserves, sensors, and reserve-overlap rows are intentionally
    excluded because they do not exist in the target ORM/migration contract.
    The supported farm-level ``overlaps_reserve`` flag remains part of the
    synthetic farm record; no intersection geometries are persisted.
    """
    dataset: dict[str, list[dict[str, Any]]] = {}
    for table, columns in DATABASE_TABLE_COLUMNS.items():
        records = generated.get(table, [])
        if table == "international_buyers":
            dataset[table] = _project(records, columns, aliases={"buyer_name": "company_name"})
        else:
            dataset[table] = _project(records, columns)
    return dataset
