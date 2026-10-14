"""AgroSense Café — UPSERT Idempotency Engine for PostgreSQL.

Builds and verifies native PostgreSQL INSERT ... ON CONFLICT SQL statements
according to the topological 5-tier ingestion order and natural business keys,
guaranteeing strict idempotency without row inflation (Deliverable E-03, CT-06).
"""

from __future__ import annotations

import enum
import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


class ConflictStrategy(enum.Enum):
    """Estrategia de resolución de conflictos en sentencias ON CONFLICT."""

    DO_NOTHING = "DO NOTHING"
    DO_UPDATE = "DO UPDATE"


@dataclass(frozen=True)
class TableUpsertConfig:
    """Configuración inmutable de UPSERT para una tabla operacional.

    Attributes:
        table_name: Nombre físico de la tabla en PostgreSQL.
        conflict_target: Tupla con la(s) columna(s) que definen la clave única de negocio.
        strategy: Estrategia a aplicar (DO NOTHING o DO UPDATE).
        update_columns: Columnas a actualizar en caso de conflicto (excluyendo claves primarias).
        tier: Nivel topológico de inserción (1 a 5).
    """

    table_name: str
    conflict_target: tuple[str, ...]
    strategy: ConflictStrategy
    update_columns: tuple[str, ...]
    tier: int


# Mapeo exhaustivo de tablas y políticas UPSERT según specifying_idempotent.md (CT-06)
TABLE_UPSERT_REGISTRY: dict[str, TableUpsertConfig] = {
    # Tier 1: Catálogos maestros independientes y actores
    "departments": TableUpsertConfig(
        table_name="departments",
        conflict_target=("dane_code",),
        strategy=ConflictStrategy.DO_NOTHING,
        update_columns=(),
        tier=1,
    ),
    "users": TableUpsertConfig(
        table_name="users",
        conflict_target=("user_id",),
        strategy=ConflictStrategy.DO_UPDATE,
        update_columns=("full_name", "role"),
        tier=1,
    ),
    "producers": TableUpsertConfig(
        table_name="producers",
        conflict_target=("document_number",),
        strategy=ConflictStrategy.DO_UPDATE,
        update_columns=(
            "full_name",
            "phone_number",
            "cooperative_join_date",
        ),
        tier=1,
    ),
    "international_buyers": TableUpsertConfig(
        table_name="international_buyers",
        conflict_target=("client_id",),
        strategy=ConflictStrategy.DO_UPDATE,
        update_columns=("buyer_name",),
        tier=1,
    ),
    "coffee_varieties": TableUpsertConfig(
        table_name="coffee_varieties",
        conflict_target=("variety_name",),
        strategy=ConflictStrategy.DO_NOTHING,
        update_columns=(),
        tier=1,
    ),
    "crop_nutrient_references": TableUpsertConfig(
        table_name="crop_nutrient_references",
        conflict_target=("reference_id",),
        strategy=ConflictStrategy.DO_UPDATE,
        update_columns=(
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
        tier=1,
    ),
    "sensor_types": TableUpsertConfig(
        table_name="sensor_types",
        conflict_target=("type_code",),
        strategy=ConflictStrategy.DO_NOTHING,
        update_columns=(),
        tier=1,
    ),
    # Tier 2: Entidades espaciales y regionales
    "municipalities": TableUpsertConfig(
        table_name="municipalities",
        conflict_target=("municipality_id",),
        strategy=ConflictStrategy.DO_UPDATE,
        update_columns=("name",),
        tier=2,
    ),
    "forest_reserves": TableUpsertConfig(
        table_name="forest_reserves",
        conflict_target=("reserve_id",),
        strategy=ConflictStrategy.DO_UPDATE,
        update_columns=(
            "name",
            "protection_category",
            "area_ha",
            "geom_ewkt",
            "polygon_geojson",
            "boundary_geojson",
        ),
        tier=2,
    ),
    # Tier 3: Entidades agrícolas principales
    "farms": TableUpsertConfig(
        table_name="farms",
        conflict_target=("farm_code",),
        strategy=ConflictStrategy.DO_UPDATE,
        update_columns=(
            "latitude",
            "longitude",
            "cultivated_area_ha",
            "water_usage_m3_ton",
            "overlaps_reserve",
        ),
        tier=3,
    ),
    "farm_plots": TableUpsertConfig(
        table_name="farm_plots",
        conflict_target=("plot_id",),
        strategy=ConflictStrategy.DO_UPDATE,
        update_columns=(
            "plot_name",
            "crop_age_years",
            "growth_stage",
        ),
        tier=3,
    ),
    "farm_reserve_overlaps": TableUpsertConfig(
        table_name="farm_reserve_overlaps",
        conflict_target=("overlap_id",),
        strategy=ConflictStrategy.DO_NOTHING,
        update_columns=(),
        tier=3,
    ),
    # Tier 4: Hardware IoT, suelos y entregas
    "iot_sensors": TableUpsertConfig(
        table_name="iot_sensors",
        conflict_target=("serial_number",),
        strategy=ConflictStrategy.DO_UPDATE,
        update_columns=(
            "status",
            "health_status",
            "battery_level",
            "battery_level_pct",
            "clock_drift_seconds",
            "last_seen_at",
            "last_transmission_at",
            "firmware_version",
        ),
        tier=4,
    ),
    "soil_lab_analyses": TableUpsertConfig(
        table_name="soil_lab_analyses",
        conflict_target=("analysis_id",),
        strategy=ConflictStrategy.DO_UPDATE,
        update_columns=(
            "ph_level",
            "ph_value",
            "nitrogen_ppm",
            "nitrogen_mg_kg",
            "phosphorus_ppm",
            "phosphorus_mg_kg",
            "potassium_cmol_kg",
            "potassium_mg_kg",
            "organic_matter_pct",
            "soil_texture",
            "raw_unit_reported",
        ),
        tier=4,
    ),
    "fertilizer_recommendations": TableUpsertConfig(
        table_name="fertilizer_recommendations",
        conflict_target=("recommendation_id",),
        strategy=ConflictStrategy.DO_UPDATE,
        update_columns=(
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
        ),
        tier=4,
    ),
    "harvest_deliveries": TableUpsertConfig(
        table_name="harvest_deliveries",
        conflict_target=("delivery_id",),
        strategy=ConflictStrategy.DO_UPDATE,
        update_columns=("farm_id", "plot_id", "delivery_date", "delivered_weight_kg"),
        tier=4,
    ),
    # Tier 5: Trazabilidad, lotes comerciales y contratos
    "export_batches": TableUpsertConfig(
        table_name="export_batches",
        conflict_target=("batch_code",),
        strategy=ConflictStrategy.DO_UPDATE,
        update_columns=(
            "total_weight_kg",
            "traced_weight_kg",
            "is_exportable",
            "is_certified",
            "weighted_water_m3_ton",
        ),
        tier=5,
    ),
    "batch_farm_compositions": TableUpsertConfig(
        table_name="batch_farm_compositions",
        conflict_target=("composition_id",),
        strategy=ConflictStrategy.DO_NOTHING,
        update_columns=(),
        tier=5,
    ),
    "buyer_batch_contracts": TableUpsertConfig(
        table_name="buyer_batch_contracts",
        conflict_target=("contract_id",),
        strategy=ConflictStrategy.DO_NOTHING,
        update_columns=(),
        tier=5,
    ),
    "agronomic_alerts": TableUpsertConfig(
        table_name="agronomic_alerts",
        conflict_target=("alert_id",),
        strategy=ConflictStrategy.DO_UPDATE,
        update_columns=("plot_id", "rule_code", "alert_type", "severity", "forecast_target_date"),
        tier=5,
    ),
}

# Orden topológico de ejecución estricto (Tier 1 a Tier 5)
TOPOLOGICAL_TABLE_ORDER: list[str] = sorted(
    TABLE_UPSERT_REGISTRY.keys(),
    key=lambda t: (
        TABLE_UPSERT_REGISTRY[t].tier,
        {
            "coffee_varieties": 0,
            "crop_nutrient_references": 1,
            "iot_sensors": 0,
            "soil_lab_analyses": 1,
            "fertilizer_recommendations": 2,
            "harvest_deliveries": 3,
        }.get(t, 10),
        t,
    ),
)


class UpsertEngine:
    """Motor de generación y verificación de sentencias UPSERT (ON CONFLICT).

    Implementa el estándar de idempotencia estricta de PostgreSQL sin inflación de filas
    cumpliendo con el criterio de aceptación CT-06.
    """

    def __init__(self, batch_size: int = 1000) -> None:
        """Inicializa el motor UPSERT con el tamaño de lote configurado.

        Args:
            batch_size: Cantidad de filas por sentencia multi-row INSERT.
        """
        if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size <= 0:
            raise ValueError("batch_size debe ser un entero positivo.")
        self.batch_size = batch_size

    @staticmethod
    def format_sql_value(val: Any, col_name: str = "") -> str:
        """Convierte y escapa de forma segura un valor de Python a literal SQL PostgreSQL.

        Args:
            val: Valor a formatear.
            col_name: Nombre opcional de la columna para aplicar casts específicos.

        Returns:
            str: Literal SQL formateado.
        """
        if val is None:
            return "NULL"
        if isinstance(val, bool):
            return "TRUE" if val else "FALSE"
        if isinstance(val, Decimal):
            if not val.is_finite():
                raise ValueError("Los valores Decimal deben ser finitos.")
            return str(val)
        if isinstance(val, int | float):
            return str(val)
        if isinstance(val, dict | list):
            serialized = json.dumps(val, ensure_ascii=False).replace("'", "''")
            return f"'{serialized}'::jsonb"
        if isinstance(val, str):
            # Formateo de geometrías PostGIS EWKT
            if (col_name in {"geom_ewkt", "geom"} or col_name.endswith("_ewkt")) and val.startswith(
                "SRID="
            ):
                escaped = val.replace("'", "''")
                return f"ST_GeomFromEWKT('{escaped}')"
            escaped = val.replace("'", "''")
            return f"'{escaped}'"
        escaped = str(val).replace("'", "''")
        return f"'{escaped}'"

    def build_upsert_sql(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        batch_size: int | None = None,
    ) -> list[str]:
        """Construye las sentencias SQL INSERT ... ON CONFLICT por lotes.

        Args:
            table_name: Nombre de la tabla destino en TABLE_UPSERT_REGISTRY.
            records: Lista de diccionarios con los registros a insertar/actualizar.
            batch_size: Tamaño de lote opcional (por defecto usa self.batch_size).

        Returns:
            list[str]: Lista de sentencias SQL formateadas y listas para ejecutar.
        """
        if not records:
            return []

        config = TABLE_UPSERT_REGISTRY.get(table_name)
        if not config:
            raise ValueError(f"Tabla no registrada en TABLE_UPSERT_REGISTRY: {table_name}")

        chunk_size = batch_size or self.batch_size
        columns = list(records[0].keys())
        col_names_str = ", ".join(columns)
        target_str = ", ".join(config.conflict_target)

        # Cláusula de conflicto
        if config.strategy == ConflictStrategy.DO_NOTHING or not config.update_columns:
            conflict_clause = f"ON CONFLICT ({target_str}) DO NOTHING"
        else:
            updates = [f"{col} = EXCLUDED.{col}" for col in config.update_columns if col in columns]
            if not updates:
                conflict_clause = f"ON CONFLICT ({target_str}) DO NOTHING"
            else:
                update_set_str = ", ".join(updates)
                conflict_clause = f"ON CONFLICT ({target_str}) DO UPDATE SET {update_set_str}"

        statements: list[str] = []
        for i in range(0, len(records), chunk_size):
            chunk = records[i : i + chunk_size]
            row_values: list[str] = []
            for row in chunk:
                formatted_vals = [
                    self.format_sql_value(row.get(col), col_name=col) for col in columns
                ]
                row_values.append(f"    ({', '.join(formatted_vals)})")

            values_block = ",\n".join(row_values)
            sql = (
                f"INSERT INTO {config.table_name} ({col_names_str})\n"
                f"VALUES\n{values_block}\n"
                f"{conflict_clause};"
            )
            statements.append(sql)

        return statements

    def build_all_upsert_statements(
        self, dataset: dict[str, list[dict[str, Any]]]
    ) -> dict[str, list[str]]:
        """Construye todas las sentencias SQL respetando el orden topológico de 5 niveles.

        Args:
            dataset: Diccionario {table_name: list_of_records}.

        Returns:
            dict[str, list[str]]: Sentencias SQL generadas agrupadas por tabla en orden topológico.
        """
        all_statements: dict[str, list[str]] = {}
        for table in TOPOLOGICAL_TABLE_ORDER:
            records = dataset.get(table, [])
            if records:
                all_statements[table] = self.build_upsert_sql(table, records)
        return all_statements

    @staticmethod
    def build_truncate_sql(table_names: list[str] | None = None) -> str:
        """Genera sentencia TRUNCATE TABLE ... RESTART IDENTITY CASCADE para reset seguro.

        Args:
            table_names: Lista opcional de tablas (por defecto usa todas las registradas).

        Returns:
            str: Sentencia SQL de truncamiento atómico.
        """
        tables = table_names or list(reversed(TOPOLOGICAL_TABLE_ORDER))
        tables_str = ", ".join(tables)
        return f"TRUNCATE TABLE {tables_str} RESTART IDENTITY CASCADE;"

    @staticmethod
    def simulate_upsert(
        table_name: str,
        existing_store: dict[tuple[Any, ...], dict[str, Any]],
        incoming_records: list[dict[str, Any]],
    ) -> dict[str, int]:
        """Simula en memoria la ejecución estricta de un UPSERT en PostgreSQL.

        Args:
            table_name: Nombre de la tabla en TABLE_UPSERT_REGISTRY.
            existing_store: Almacén de estado mutable indexado por clave de conflicto.
            incoming_records: Nuevos registros a procesar.

        Returns:
            dict[str, int]: Estadísticas de inserción, actualización e invariancia.
        """
        config = TABLE_UPSERT_REGISTRY.get(table_name)
        if not config:
            raise ValueError(f"Tabla no registrada: {table_name}")

        stats = {"inserted": 0, "updated": 0, "unchanged": 0}

        for record in incoming_records:
            key = tuple(record.get(col) for col in config.conflict_target)
            if key in existing_store:
                if config.strategy == ConflictStrategy.DO_UPDATE and config.update_columns:
                    current_record = existing_store[key]
                    changed = False
                    for col in config.update_columns:
                        if col in record and record[col] != current_record.get(col):
                            current_record[col] = record[col]
                            changed = True
                    if changed:
                        stats["updated"] += 1
                    else:
                        stats["unchanged"] += 1
                else:
                    # DO NOTHING
                    stats["unchanged"] += 1
            else:
                existing_store[key] = dict(record)
                stats["inserted"] += 1

        return stats

    def verify_idempotency(self, dataset: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        """Valida rigurosamente la idempotencia sin inflación de filas (CT-06).

        Ejecuta dos pasadas consecutivas con el mismo dataset:
        1. Pasada 1 (Carga inicial): Registra las filas insertadas y el checksum de cada tabla.
        2. Pasada 2 (Re-ejecución idéntica): Comprueba que el recuento final de filas sea
           exactamente igual al inicial (cero inflación) y que el checksum converja al 100%.

        Args:
            dataset: Diccionario con las colecciones sintéticas a validar.

        Returns:
            dict[str, Any]: Reporte detallado de certificación CT-06.
        """
        report: dict[str, Any] = {
            "is_idempotent": True,
            "row_inflation_detected": False,
            "tables_tested": 0,
            "table_results": {},
        }

        for table in TOPOLOGICAL_TABLE_ORDER:
            records = dataset.get(table, [])
            if not records:
                continue

            config = TABLE_UPSERT_REGISTRY[table]
            store: dict[tuple[Any, ...], dict[str, Any]] = {}

            # Pasada 1: Carga inicial
            stats_run1 = self.simulate_upsert(table, store, records)
            count_run1 = len(store)
            checksum_run1 = self._calculate_store_checksum(store)

            # Pasada 2: Re-ejecución idéntica (prueba de UPSERT)
            stats_run2 = self.simulate_upsert(table, store, records)
            count_run2 = len(store)
            checksum_run2 = self._calculate_store_checksum(store)

            # Verificación de inflación de filas
            row_inflation = count_run2 - count_run1
            has_inflation = row_inflation != 0
            checksum_match = checksum_run1 == checksum_run2

            table_valid = not has_inflation and checksum_match
            if not table_valid:
                report["is_idempotent"] = False
                report["row_inflation_detected"] = True

            report["tables_tested"] += 1
            report["table_results"][table] = {
                "initial_count": count_run1,
                "re_run_count": count_run2,
                "row_inflation": row_inflation,
                "strategy": config.strategy.value,
                "conflict_target": list(config.conflict_target),
                "checksum_run1": checksum_run1,
                "checksum_run2": checksum_run2,
                "checksum_match": checksum_match,
                "passed": table_valid,
                "pass1_stats": stats_run1,
                "pass2_stats": stats_run2,
            }

        return report

    @staticmethod
    def _calculate_store_checksum(store: dict[tuple[Any, ...], dict[str, Any]]) -> str:
        """Calcula un hash SHA-256 canónico sobre los datos ordenados del almacén."""
        sorted_keys = sorted(store.keys(), key=lambda k: str(k))
        serialized_rows: list[str] = []
        for key in sorted_keys:
            row = store[key]
            # Normalizar diccionarios ordenando claves
            row_repr = json.dumps(row, sort_keys=True, default=str)
            serialized_rows.append(row_repr)
        payload = "\n".join(serialized_rows)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def calculate_database_checksum(
        cls,
        state: dict[str, dict[tuple[Any, ...], dict[str, Any]]] | None = None,
    ) -> str:
        """Calcula un checksum SHA-256 consolidado sobre todas las tablas (CT-06).

        Ordena topológicamente las colecciones para garantizar determinismo estricto.

        Args:
            state: Almacén de tablas opcional. Por defecto usa _GLOBAL_DATABASE_STORE.

        Returns:
            str: Hash SHA-256 consolidado y determinista.
        """
        active_state = state if state is not None else _GLOBAL_DATABASE_STORE
        table_hashes: list[str] = []
        for table in TOPOLOGICAL_TABLE_ORDER:
            if table in active_state:
                store = active_state[table]
                store_hash = cls._calculate_store_checksum(store)
                table_hashes.append(f"{table}:{store_hash}")
        payload = "\n".join(table_hashes)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def apply_dataset_upsert(
        self, dataset: dict[str, list[dict[str, Any]]]
    ) -> dict[str, dict[str, int]]:
        """Aplica el dataset contra el almacén global simulado de la base de datos.

        Args:
            dataset: Diccionario con los registros sintéticos a insertar/actualizar.

        Returns:
            dict[str, dict[str, int]]: Estadísticas de inserción/actualización por tabla.
        """
        summary_stats: dict[str, dict[str, int]] = {}
        for table in TOPOLOGICAL_TABLE_ORDER:
            records = dataset.get(table, [])
            if records:
                table_store = _GLOBAL_DATABASE_STORE.setdefault(table, {})
                stats = self.simulate_upsert(table, table_store, records)
                summary_stats[table] = stats
        return summary_stats


# Almacén global en memoria que simula la base de datos PostgreSQL persistente
_GLOBAL_DATABASE_STORE: dict[str, dict[tuple[Any, ...], dict[str, Any]]] = {}


def get_database_state() -> dict[str, dict[tuple[Any, ...], dict[str, Any]]]:
    """Retorna una referencia al almacén global de la base de datos simulada."""
    return _GLOBAL_DATABASE_STORE


def get_database_row_counts() -> dict[str, int]:
    """Retorna un mapeo con el recuento actual de filas por tabla en la base de datos."""
    return {table: len(store) for table, store in _GLOBAL_DATABASE_STORE.items()}


def reset_database_state() -> None:
    """Limpia todo el estado de la base de datos simulada (emula TRUNCATE CASCADE)."""
    _GLOBAL_DATABASE_STORE.clear()


def calculate_database_checksum(
    state: dict[str, dict[tuple[Any, ...], dict[str, Any]]] | None = None,
) -> str:
    """Calcula el hash SHA-256 canónico del estado completo de la base de datos (CT-06).

    Args:
        state: Estado opcional de tablas. Si es None, utiliza _GLOBAL_DATABASE_STORE.

    Returns:
        str: Checksum SHA-256 consolidado y determinista.
    """
    return UpsertEngine.calculate_database_checksum(state)
