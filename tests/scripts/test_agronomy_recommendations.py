from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from agrosense_api.models import Base
from agrosense_api.services.agronomy import (
    evaluate_fertilizer_recommendation,
    normalize_soil_lab_values,
)

from scripts.seed.database_dataset import DATABASE_TABLE_COLUMNS, build_database_dataset
from scripts.seed.faker_generators import AgroSenseFakerGenerator
from scripts.seed.upsert_engine import (
    TABLE_UPSERT_REGISTRY,
    TOPOLOGICAL_TABLE_ORDER,
    UpsertEngine,
)

ANALYSIS = {
    "ph_level": 5.4,
    "nitrogen_mg_kg": 40,
    "phosphorus_mg_kg": 20,
    "potassium_mg_kg": 70,
}
REFERENCE = {
    "n_min_mg_kg": 100,
    "n_max_mg_kg": 160,
    "p_min_mg_kg": 50,
    "p_max_mg_kg": 80,
    "k_min_mg_kg": 100,
    "k_max_mg_kg": 150,
    "target_ph_min": 5.0,
    "target_ph_max": 5.8,
}


def test_fertilizer_recommendation_deficient():
    result = evaluate_fertilizer_recommendation(ANALYSIS, REFERENCE)

    assert result["n_evaluation"] == "DEFICIENT"
    assert result["recommended_n_kg_ha"] == Decimal("30.00")
    assert result["recommended_p_kg_ha"] == Decimal("15.00")
    assert result["recommended_k_kg_ha"] == Decimal("15.00")
    assert result["estimated_saving_pct"] > 0
    assert result["apply_fertilizer"] is True


def test_fertilizer_recommendation_excess_warning():
    analysis = {**ANALYSIS, "nitrogen_mg_kg": 200}
    result = evaluate_fertilizer_recommendation(analysis, REFERENCE)

    assert result["n_evaluation"] == "EXCESS_WARNING"
    assert result["recommended_n_kg_ha"] == Decimal("0.00")
    assert result["apply_fertilizer"] is False
    assert "No aplicar fertilizante nitrogenado" in result["warning_message"]


def test_identical_recommendation_across_normalized_units():
    from_ppm = normalize_soil_lab_values(
        nitrogen_value=40,
        nitrogen_unit="ppm",
        phosphorus_value=20,
        phosphorus_unit="ppm",
        potassium_value=Decimal("0.5"),
        potassium_unit="cmol/kg",
    )
    from_mg_kg = normalize_soil_lab_values(
        nitrogen_value=40,
        nitrogen_unit="mg/kg",
        phosphorus_value=20,
        phosphorus_unit="mg/kg",
        potassium_value=Decimal("195.49"),
        potassium_unit="mg/kg",
    )
    ppm_result = evaluate_fertilizer_recommendation({**ANALYSIS, **from_ppm}, REFERENCE)
    mg_kg_result = evaluate_fertilizer_recommendation({**ANALYSIS, **from_mg_kg}, REFERENCE)

    assert ppm_result == mg_kg_result


def test_generator_creates_one_deterministic_recommendation_per_analysis():
    generator = AgroSenseFakerGenerator(seed=42)
    analysis = {
        **ANALYSIS,
        "analysis_id": generator.get_uuid5("analysis-1"),
        "farm_id": "farm-1",
        "plot_id": "plot-1",
    }
    plot = {
        "plot_id": "plot-1",
        "farm_id": "farm-1",
        "variety_id": 1,
        "growth_stage": "VEGETATIVE",
    }
    reference = {
        **REFERENCE,
        "variety_id": 1,
        "growth_stage": "VEGETATIVE",
    }

    first = generator.generate_fertilizer_recommendations([analysis], [plot], [reference])
    second = generator.generate_fertilizer_recommendations([analysis], [plot], [reference])

    assert first == second
    assert len(first) == 1
    assert first[0]["analysis_id"] == analysis["analysis_id"]


def test_seed_rows_match_agronomy_orm_columns():
    dataset = AgroSenseFakerGenerator(seed=42).generate_all(mode="dev")
    for table_name in (
        "crop_nutrient_references",
        "soil_lab_analyses",
        "fertilizer_recommendations",
        "agronomic_alerts",
    ):
        model_columns = set(Base.metadata.tables[table_name].columns.keys())
        for record in dataset[table_name]:
            assert record.keys() <= model_columns

    assert len(dataset["soil_lab_analyses"]) == len(dataset["fertilizer_recommendations"])


def test_database_dataset_projects_only_current_orm_tables_and_columns():
    generated = AgroSenseFakerGenerator(seed=42).generate_all(mode="dev")
    dataset = build_database_dataset(generated)

    assert set(dataset) == set(DATABASE_TABLE_COLUMNS)
    for table_name, records in dataset.items():
        model_columns = set(Base.metadata.tables[table_name].columns.keys())
        assert all(record.keys() <= model_columns for record in records)
        assert all(set(record) == set(DATABASE_TABLE_COLUMNS[table_name]) for record in records)
    assert "departments" not in dataset
    assert "farm_reserve_overlaps" not in dataset
    assert dataset["international_buyers"][0]["buyer_name"]
    assert "company_name" not in dataset["international_buyers"][0]


@pytest.mark.parametrize(
    ("variable", "alert_type", "rule_code"),
    [
        ("SEED_FORCE_ROYA_FARMS", "COFFEE_RUST", "RN-03"),
        ("SEED_FORCE_DEFICIT_FARMS", "WATER_DEFICIT", "RN-04"),
        ("SEED_FORCE_EXTREME_RAIN_FARMS", "EXTREME_RAIN", "RN-05"),
    ],
)
def test_forced_alert_variables_generate_expected_alert(
    monkeypatch, variable, alert_type, rule_code
):
    for name in (
        "SEED_FORCE_ROYA_FARMS",
        "SEED_FORCE_DEFICIT_FARMS",
        "SEED_FORCE_EXTREME_RAIN_FARMS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(variable, "F-001")
    generator = AgroSenseFakerGenerator(seed=42)
    farms = [{"farm_id": "farm-1", "farm_code": "F-001"}]
    plots = [{"farm_id": "farm-1", "plot_id": "plot-1"}]

    alerts = generator.generate_agronomic_alerts(
        farms, plots, forecast_target_date=date(2026, 10, 20)
    )
    alert = next(item for item in alerts if item["alert_type"] == alert_type)

    assert alert["rule_code"] == rule_code
    assert alert["alert_id"] == generator.get_uuid5(f"F-001:{alert_type}:2026-10-20")


def test_forced_alert_rejects_unknown_farm_code(monkeypatch):
    monkeypatch.setenv("SEED_FORCE_ROYA_FARMS", "F-UNKNOWN")
    monkeypatch.delenv("SEED_FORCE_DEFICIT_FARMS", raising=False)
    monkeypatch.delenv("SEED_FORCE_EXTREME_RAIN_FARMS", raising=False)
    generator = AgroSenseFakerGenerator(seed=42)

    with pytest.raises(ValueError, match="farm_code desconocidos"):
        generator.generate_agronomic_alerts([{"farm_id": "farm-1", "farm_code": "F-001"}], [])


def test_upsert_tiers_and_update_strategies_are_registered():
    assert TOPOLOGICAL_TABLE_ORDER.index("soil_lab_analyses") < TOPOLOGICAL_TABLE_ORDER.index(
        "fertilizer_recommendations"
    )
    assert TABLE_UPSERT_REGISTRY["fertilizer_recommendations"].conflict_target == (
        "recommendation_id",
    )
    assert TABLE_UPSERT_REGISTRY["fertilizer_recommendations"].strategy.value == "DO UPDATE"
    assert TABLE_UPSERT_REGISTRY["agronomic_alerts"].conflict_target == ("alert_id",)
    assert TABLE_UPSERT_REGISTRY["agronomic_alerts"].strategy.value == "DO UPDATE"

    engine = UpsertEngine()
    sql = engine.build_upsert_sql(
        "fertilizer_recommendations",
        [
            {
                "recommendation_id": "rec-1",
                "analysis_id": "analysis-1",
                "estimated_saving_pct": Decimal("70.00"),
            }
        ],
    )[0]
    assert "ON CONFLICT (recommendation_id) DO UPDATE SET" in sql
    assert "estimated_saving_pct = EXCLUDED.estimated_saving_pct" in sql

    alert_sql = engine.build_upsert_sql(
        "agronomic_alerts",
        [
            {
                "alert_id": "alert-1",
                "farm_id": "farm-1",
                "alert_type": "COFFEE_RUST",
                "severity": "HIGH",
                "status": "OPEN",
            }
        ],
    )[0]
    assert "ON CONFLICT (alert_id) DO UPDATE SET" in alert_sql
    assert "severity = EXCLUDED.severity" in alert_sql
    assert "status = EXCLUDED.status" not in alert_sql


def test_upsert_simulation_is_idempotent_for_recommendations_and_alerts():
    engine = UpsertEngine()
    records = {
        "fertilizer_recommendations": [
            {
                "recommendation_id": "rec-1",
                "estimated_saving_pct": Decimal("70.00"),
            }
        ],
        "agronomic_alerts": [
            {
                "alert_id": "alert-1",
                "alert_type": "COFFEE_RUST",
                "status": "OPEN",
            }
        ],
    }

    report = engine.verify_idempotency(records)

    assert report["is_idempotent"] is True
    assert report["row_inflation_detected"] is False
    assert report["tables_tested"] == 2
    assert all(item["checksum_match"] for item in report["table_results"].values())


def test_alert_upsert_preserves_operational_status():
    store = {
        ("alert-1",): {
            "alert_id": "alert-1",
            "severity": "LOW",
            "status": "RESOLVED",
        }
    }

    stats = UpsertEngine.simulate_upsert(
        "agronomic_alerts",
        store,
        [{"alert_id": "alert-1", "severity": "HIGH", "status": "OPEN"}],
    )

    assert stats == {"inserted": 0, "updated": 1, "unchanged": 0}
    assert store[("alert-1",)]["severity"] == "HIGH"
    assert store[("alert-1",)]["status"] == "RESOLVED"
