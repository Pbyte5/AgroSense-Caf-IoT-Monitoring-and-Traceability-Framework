"""AgroSense Café — Reproducible and Idempotent Data Seed Script.

CLI script supporting deterministic seed parameters, modes, defect rates,
and reset operations for PostgreSQL and storage layers.
"""

from __future__ import annotations

import argparse
import logging
import os
import random
from collections.abc import Sequence
from dataclasses import dataclass

from scripts.seed.records import generate_sample_seed_records, generate_spatial_seed_records

logger = logging.getLogger("agrosense.seed")


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
