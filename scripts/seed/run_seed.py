"""AgroSense Café — Reproducible and Idempotent Data Seed Script.

CLI script supporting deterministic seed parameters, modes, defect rates,
and reset operations for PostgreSQL and storage layers.
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from scripts.seed.spatial import PostGISSpatialGenerator

logger = logging.getLogger("agrosense.seed")

# Namespace oficial para generación determinista de identificadores UUIDv5 (Deliverable E-03, CT-06)
AGROSENSE_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


@dataclass(frozen=True)
class SeedConfig:
    """Configuración inmutable de ejecución para el proceso de seeding.

    Attributes:
        mode: Escala del dataset ('dev' para desarrollo local o 'prod' para volumen completo).
        seed: Semilla entera fija para generadores de números pseudoaleatorios (PRNG).
        defect_rate: Proporción de defectos y anomalías sintéticas a inyectar (0.0 a 1.0).
        reset: Indica si se debe ejecutar un borrado seguro (TRUNCATE CASCADE) previo a la carga.
    """

    mode: str
    seed: int
    defect_rate: float
    reset: bool = False


def set_reproducible_state(seed: int) -> None:
    """Fija la semilla en los generadores globales para garantizar reproducibilidad determinista.

    Inicializa los generadores pseudoaleatorios del sistema con la semilla especificada,
    cumpliendo con la especificación de reproducibilidad (Deliverable E-03, CT-06).

    Args:
        seed: Número entero para inicializar el estado del PRNG.
    """
    logger.debug("Fijando estado reproducible con semilla=%d", seed)
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


def validate_defect_rate(val: str) -> float:
    """Valida y convierte la tasa de defectos ingresada por CLI.

    Garantiza que el valor sea un número decimal acotado en el intervalo [0.0, 1.0].

    Args:
        val: Cadena de texto recibida desde el argumento CLI.

    Returns:
        float: Valor decimal validado entre 0.0 y 1.0.

    Raises:
        argparse.ArgumentTypeError: Si el valor no es numérico o está fuera de rango.
    """
    try:
        fval = float(val)
    except ValueError as err:
        msg = f"La tasa de defectos debe ser un float, recibido: {val!r}"
        raise argparse.ArgumentTypeError(msg) from err

    if not 0.0 <= fval <= 1.0:
        raise argparse.ArgumentTypeError(
            f"La tasa de defectos debe estar entre 0.0 y 1.0, recibido: {fval}"
        )
    return fval


def build_parser() -> argparse.ArgumentParser:
    """Construye y configura el parser de argumentos de línea de comandos (CLI).

    Configura los parámetros admitidos y lee las variables de entorno como valores
    por defecto en caso de no ser provistos explícitamente en la terminal.

    Returns:
        argparse.ArgumentParser: Objeto parser listo para procesar argumentos.
    """
    # 1. Obtener valores por defecto desde variables de entorno (con fallbacks seguros)
    env_mode = os.getenv("SEED_PROFILE", "dev").lower()
    default_mode = env_mode if env_mode in {"dev", "prod"} else "dev"

    try:
        default_seed = int(os.getenv("SEED_RANDOM_STATE", "42"))
    except ValueError:
        default_seed = 42

    try:
        default_defect_rate = float(os.getenv("SEED_DEFECT_GLOBAL_RATE", "0.05"))
        if not 0.0 <= default_defect_rate <= 1.0:
            default_defect_rate = 0.05
    except ValueError:
        default_defect_rate = 0.05

    # 2. Definición del parser con descripción del entregable
    parser = argparse.ArgumentParser(
        prog="run_seed.py",
        description=(
            "AgroSense Café - Ejecutor reproducible e idempotente de datos sintéticos. "
            "Puebla la base de datos PostgreSQL y las capas de almacenamiento."
        ),
    )

    # Argumento: --mode
    parser.add_argument(
        "--mode",
        choices=["dev", "prod"],
        default=default_mode,
        help=(
            f"Perfil de volumen: 'dev' (ligero para pruebas locales) "
            f"o 'prod' (volumen completo). Por defecto: {default_mode}."
        ),
    )

    # Argumento: --seed
    parser.add_argument(
        "--seed",
        type=int,
        default=default_seed,
        help=(
            f"Semilla entera para el PRNG para asegurar determinismo. Por defecto: {default_seed}."
        ),
    )

    # Argumento: --defect-rate
    parser.add_argument(
        "--defect-rate",
        type=validate_defect_rate,
        default=default_defect_rate,
        dest="defect_rate",
        help=(
            f"Proporción de defectos de calidad a inyectar (0.0 a 1.0). "
            f"Por defecto: {default_defect_rate}."
        ),
    )

    # Argumento: --reset
    parser.add_argument(
        "--reset",
        action="store_true",
        default=False,
        help="Limpia las tablas y reinicia secuencias antes de sembrar (TRUNCATE CASCADE).",
    )

    return parser


def parse_args(args: Sequence[str] | None = None) -> SeedConfig:
    """Parsea y valida los argumentos CLI, retornando una configuración inmutable.

    Args:
        args: Lista opcional de argumentos a parsear (None para usar sys.argv).

    Returns:
        SeedConfig: Objeto de configuración validado.
    """
    parser = build_parser()
    parsed = parser.parse_args(args)
    return SeedConfig(
        mode=parsed.mode,
        seed=parsed.seed,
        defect_rate=parsed.defect_rate,
        reset=parsed.reset,
    )


def generate_sample_seed_records(count: int = 5) -> list[dict[str, Any]]:
    """Genera una muestra sintética de registros usando la semilla y UUIDv5 deterministas.

    Crea una lista de prueba con fincas simuladas siguiendo el esquema oficial
    de AgroSense Café (data_structure.md) para verificar el determinismo.

    Args:
        count: Número de registros sintéticos a generar (por defecto 5 para pruebas).

    Returns:
        list[dict[str, Any]]: Lista de diccionarios con los registros de prueba generados.
    """
    sample_records: list[dict[str, Any]] = []

    for i in range(1, count + 1):
        farm_code = f"FIN-{i:04d}"
        # Generación determinista de UUIDv5 según especificación del proyecto
        farm_id = str(uuid.uuid5(AGROSENSE_NAMESPACE, farm_code))

        # Valores generados usando el estado PRNG fijado por la semilla
        altitude = random.randint(1200, 1950)
        total_area = round(random.uniform(2.5, 25.0), 2)
        has_sensors = random.random() < 0.3  # 30% aprox de fincas con sensores piloto

        record = {
            "farm_id": farm_id,
            "farm_code": farm_code,
            "name": f"Hacienda Cafetera {i}",
            "altitude_msl": altitude,
            "total_area_ha": total_area,
            "has_pilot_sensors": has_sensors,
        }
        sample_records.append(record)

    return sample_records


def generate_spatial_seed_records(
    farms: list[dict[str, Any]], seed: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Attach deterministic PostGIS-ready boundaries to farms and generate reserves.

    Geometry is returned as EWKT (for ``ST_GeomFromEWKT``) and GeoJSON (for the
    project's JSONB ``polygon_geojson`` columns). These are synthetic seed records;
    this function does not connect to or write into a database.
    """
    if not isinstance(farms, list) or any(not isinstance(farm, dict) for farm in farms):
        raise ValueError("farms debe ser una lista de registros tipo diccionario.")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed debe ser un entero.")
    generator = PostGISSpatialGenerator(seed=seed)
    reserves = generator.generate_forest_reserves(count=min(len(farms), 5))
    reserve_records = [
        {
            "reserve_id": reserve.entity_id,
            "reserve_code": reserve.entity_code,
            "name": reserve.name,
            "area_ha": reserve.area_ha,
            "srid": reserve.srid,
            "geom_ewkt": reserve.ewkt,
            "polygon_geojson": reserve.geojson,
        }
        for reserve in reserves
    ]

    farm_records: list[dict[str, Any]] = []
    for farm in farms:
        polygon = generator.generate_farm_polygon(
            farm_code=farm["farm_code"],
            name=farm["name"],
            area_ha=farm["total_area_ha"],
        )
        overlaps = any(
            generator.polygons_intersect(polygon.points, reserve.points) for reserve in reserves
        )
        farm_records.append(
            {
                **farm,
                "latitude": polygon.center_lat,
                "longitude": polygon.center_lon,
                "has_valid_coords": polygon.is_valid_coords,
                "overlaps_reserve": overlaps,
                "srid": polygon.srid,
                "geom_ewkt": polygon.ewkt,
                "polygon_geojson": polygon.geojson,
            }
        )
    return farm_records, reserve_records


def run_seed(config: SeedConfig) -> int:
    """Orquesta y ejecuta el proceso de generación y siembra de datos.

    Args:
        config: Parámetros validados para la ejecución del seed.

    Returns:
        int: Código de salida (0 para éxito, distinto de 0 en caso de error).
    """
    try:
        logger.info("Iniciando proceso de seeding de AgroSense Café...")
        logger.info(
            "Configuración activa: mode=%s, seed=%d, defect_rate=%.2f, reset=%s",
            config.mode,
            config.seed,
            config.defect_rate,
            config.reset,
        )

        # 1. Asegurar estado pseudoaleatorio determinista con la semilla configurada
        set_reproducible_state(config.seed)

        # 2. Crear lista vacía y poblarla con una muestra sintética para testear
        sample_data, reserve_data = generate_spatial_seed_records(
            generate_sample_seed_records(count=5), seed=config.seed
        )
        logger.info(
            "Muestra sintética generada exitosamente (%d registros):",
            len(sample_data),
        )
        for item in sample_data:
            logger.info(
                "  -> %s [%s] | Altitud: %d msnm | Área: %.2f ha | Sensores: %s",
                item["farm_code"],
                item["farm_id"][:8] + "...",
                item["altitude_msl"],
                item["total_area_ha"],
                item["has_pilot_sensors"],
            )

        logger.info(
            "Geometrías generadas: %d fincas y %d reservas forestales (SRID=%d).",
            len(sample_data),
            len(reserve_data),
            4326,
        )

        logger.info("Proceso de seeding finalizado con éxito.")
        return 0
    except Exception as err:
        logger.error("Error crítico durante la ejecución del seed: %s", err, exc_info=True)
        return 1


def main(argv: Sequence[str] | None = None) -> None:
    """Punto de entrada principal para el ejecutor CLI.

    Configura el sistema de logging estándar de la aplicación y despacha la ejecución.

    Args:
        argv: Lista opcional de argumentos para el parser.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    )
    config = parse_args(argv)
    exit_code = run_seed(config)
    if exit_code != 0:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
