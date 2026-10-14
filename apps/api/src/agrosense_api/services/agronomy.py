from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

DOSAGE_QUANTUM = Decimal("0.01")
SOIL_MG_KG_TO_KG_HA_FACTOR = Decimal("0.5")
NUTRIENTS = {
    "n": ("nitrogen_mg_kg", "n_min_mg_kg", "n_max_mg_kg", "Nitrógeno", "nitrogenado"),
    "p": (
        "phosphorus_mg_kg",
        "p_min_mg_kg",
        "p_max_mg_kg",
        "Fósforo",
        "fosfatado",
    ),
    "k": ("potassium_mg_kg", "k_min_mg_kg", "k_max_mg_kg", "Potasio", "potásico"),
}


def _value(source: Any, name: str) -> Any:
    if isinstance(source, dict):
        return source[name]
    return getattr(source, name)


def _decimal(source: Any, name: str) -> Decimal:
    result = Decimal(str(_value(source, name)))
    if not result.is_finite():
        raise ValueError(f"{name} debe ser un número finito.")
    return result


def evaluate_fertilizer_recommendation(
    analysis: Any,
    reference: Any,
    *,
    traditional_baseline_kg_ha: Decimal | float = Decimal("200"),
) -> dict[str, Any]:
    """Evalúa RN-07 en mg/kg usando el factor de conversión inicial del prototipo.

    El factor suelo-a-dosis debe calibrarse con agronomía local antes de usar las
    cantidades como prescripciones de campo.
    """
    baseline = Decimal(str(traditional_baseline_kg_ha))
    if not baseline.is_finite() or baseline <= 0:
        raise ValueError("traditional_baseline_kg_ha debe ser un valor positivo y finito.")

    result: dict[str, Any] = {
        "n_evaluation": "",
        "p_evaluation": "",
        "k_evaluation": "",
        "ph_evaluation": "",
        "recommended_n_kg_ha": Decimal("0.00"),
        "recommended_p_kg_ha": Decimal("0.00"),
        "recommended_k_kg_ha": Decimal("0.00"),
        "lime_amendment_kg_ha": Decimal("0.00"),
        "apply_fertilizer": True,
        "status": "GENERATED",
    }
    any_excess = False
    warnings: list[str] = []
    for nutrient, (
        analysis_field,
        minimum_field,
        maximum_field,
        label,
        fertilizer,
    ) in NUTRIENTS.items():
        actual = _decimal(analysis, analysis_field)
        minimum = _decimal(reference, minimum_field)
        maximum = _decimal(reference, maximum_field)
        if minimum > maximum:
            raise ValueError(f"Rango F1 inválido para {nutrient.upper()}.")

        if actual < minimum:
            dose = max(
                Decimal("0"),
                (minimum - actual) * SOIL_MG_KG_TO_KG_HA_FACTOR,
            )
            result[f"{nutrient}_evaluation"] = "DEFICIENT"
            result[f"recommended_{nutrient}_kg_ha"] = dose.quantize(
                DOSAGE_QUANTUM, rounding=ROUND_HALF_UP
            )
        elif actual > maximum:
            result[f"{nutrient}_evaluation"] = "EXCESS_WARNING"
            any_excess = True
            warnings.append(
                f"Se detectó exceso de {label} en suelo. No aplicar fertilizante "
                f"{fertilizer} para evitar fitotoxicidad y acidificación."
            )
        else:
            result[f"{nutrient}_evaluation"] = "OPTIMAL"

    ph = _decimal(analysis, "ph_level")
    ph_minimum = _decimal(reference, "target_ph_min")
    ph_maximum = _decimal(reference, "target_ph_max")
    if ph_minimum > ph_maximum:
        raise ValueError("Rango F1 de pH inválido.")
    if ph < ph_minimum:
        result["ph_evaluation"] = "ACIDIC"
    elif ph > ph_maximum:
        result["ph_evaluation"] = "ALKALINE"
    else:
        result["ph_evaluation"] = "OPTIMAL"

    total_dose = sum(
        (result[f"recommended_{nutrient}_kg_ha"] for nutrient in "npk"),
        Decimal("0"),
    )
    result["apply_fertilizer"] = not any_excess and total_dose > 0
    if any_excess:
        result["status"] = "EXCESS_WARNING"
        result["warning_message"] = " ".join(warnings)
    saving = max(Decimal("0"), (baseline - total_dose) / baseline * Decimal("100"))
    result["estimated_saving_pct"] = min(
        Decimal("100"), saving.quantize(DOSAGE_QUANTUM, rounding=ROUND_HALF_UP)
    )
    return result


def normalize_soil_lab_values(
    *,
    nitrogen_value: Decimal | float | int,
    nitrogen_unit: str,
    phosphorus_value: Decimal | float | int,
    phosphorus_unit: str,
    potassium_value: Decimal | float | int,
    potassium_unit: str,
) -> dict[str, Decimal]:
    """Normaliza N/P desde ppm o mg/kg y K desde cmol/kg a mg/kg."""
    unit_factors = {
        "ppm": Decimal("1"),
        "mg/kg": Decimal("1"),
    }

    def normalize(value: Decimal | float | int, unit: str, nutrient: str) -> Decimal:
        normalized_unit = unit.strip().lower()
        if nutrient == "k" and normalized_unit == "cmol/kg":
            factor = Decimal("390.98")
        else:
            factor = unit_factors.get(normalized_unit)
            if factor is None:
                raise ValueError(f"Unidad no compatible para {nutrient.upper()}: {unit}.")
        result = Decimal(str(value)) * factor
        if not result.is_finite():
            raise ValueError(f"El valor de {nutrient.upper()} debe ser finito.")
        if result < 0:
            raise ValueError(f"El valor de {nutrient.upper()} no puede ser negativo.")
        return result

    return {
        "nitrogen_mg_kg": normalize(nitrogen_value, nitrogen_unit, "n"),
        "phosphorus_mg_kg": normalize(phosphorus_value, phosphorus_unit, "p"),
        "potassium_mg_kg": normalize(potassium_value, potassium_unit, "k"),
    }
