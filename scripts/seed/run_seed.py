"""AgroSense Café — Reproducible and Idempotent Data Seed Script.

Generates PostgreSQL UPSERT statements and simulates their effect in memory.
It does not connect to PostgreSQL or write to object storage.
"""

from __future__ import annotations

import argparse
import logging
import os
import random
from collections.abc import Sequence
from dataclasses import dataclass

from faker import Faker

from .database_dataset import build_database_dataset
from .faker_generators import AgroSenseFakerGenerator
from .records import generate_sample_seed_records, generate_spatial_seed_records
from .upsert_engine import (
    UpsertEngine,
    calculate_database_checksum,
    get_database_row_counts,
    get_database_state,
    reset_database_state,
)

logger = logging.getLogger("agrosense.seed")


@dataclass(frozen=True)
class SeedConfig:
    """Configuración inmutable de ejecución para el proceso de seeding.

    Attributes:
        mode: Escala del dataset ('dev' para desarrollo local o 'prod' para volumen completo).
        seed: Semilla entera fija para generadores de números pseudoaleatorios (PRNG).
        defect_rate: Proporción de defectos y anomalías sintéticas a inyectar (0.0 a 1.0).
        reset: Reinicia el almacén de simulación en memoria.
        batch_size: Tamaño de lote para sentencias multi-row UPSERT (por defecto 1000).
        write_postgres: Habilita explícitamente la persistencia PostgreSQL.
        reset_database: Trunca el subconjunto cargado en PostgreSQL antes de escribir.
    """

    mode: str
    seed: int
    defect_rate: float
    reset: bool = False
    batch_size: int = 1000
    write_postgres: bool = False
    reset_database: bool = False


def set_reproducible_state(seed: int) -> None:
    """Fija la semilla en los generadores globales para garantizar reproducibilidad determinista.

    Inicializa los generadores pseudoaleatorios del sistema con la semilla especificada,
    cumpliendo con la especificación de reproducibilidad (Deliverable E-03, CT-06).

    Args:
        seed: Número entero para inicializar el estado del PRNG.
    """
    logger.debug("Fijando estado reproducible con semilla=%d", seed)
    random.seed(seed)
    Faker.seed(seed)
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

    try:
        default_batch_size = int(os.getenv("SEED_DB_BATCH_SIZE", "1000"))
        if default_batch_size <= 0:
            default_batch_size = 1000
    except ValueError:
        default_batch_size = 1000

    env_reset = os.getenv("SEED_RESET_BEFORE_RUN", "false").lower() in {"true", "1", "yes"}

    # 2. Definición del parser con descripción del entregable
    parser = argparse.ArgumentParser(
        prog="run_seed.py",
        description=(
            "AgroSense Café - Generador reproducible de datos y SQL UPSERT. "
            "Por defecto simula en memoria; --write-postgres habilita escritura explícita."
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
        default=env_reset,
        help="Reinicia únicamente el almacén simulado en memoria.",
    )

    # Argumento: --batch-size
    parser.add_argument(
        "--batch-size",
        type=int,
        default=default_batch_size,
        dest="batch_size",
        help=f"Tamaño de lote para sentencias multi-row UPSERT. Por defecto: {default_batch_size}.",
    )
    parser.add_argument(
        "--write-postgres",
        action="store_true",
        help=(
            "Escribe los datos compatibles con el esquema ORM en PostgreSQL. "
            "Requiere AGROSENSE_DATABASE_URL."
        ),
    )
    parser.add_argument(
        "--reset-database",
        action="store_true",
        help=(
            "Trunca las tablas incluidas en el dataset antes de escribir. "
            "Requiere --write-postgres; no usa CASCADE."
        ),
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
        batch_size=parsed.batch_size,
        write_postgres=parsed.write_postgres,
        reset_database=parsed.reset_database,
    )


def run_seed(
    config: SeedConfig | None = None,
    *,
    seed_value: int | None = None,
    mode: str = "dev",
    defect_rate: float = 0.05,
    reset: bool = False,
    batch_size: int = 1000,
    write_postgres: bool = False,
    reset_database: bool = False,
) -> int:
    """Orquesta y ejecuta el proceso de generación y siembra de datos con Faker y UPSERT.

    Admite tanto un objeto inmutable SeedConfig como parámetros por palabra clave
    (seed_value, mode, defect_rate, reset, batch_size) para máxima compatibilidad con tests.

    Args:
        config: Parámetros validados para la ejecución del seed (opcional).
        seed_value: Semilla PRNG opcional si no se provee config.
        mode: Perfil de escala ('dev' o 'prod') si no se provee config.
        defect_rate: Proporción de defectos si no se provee config.
        reset: Limpieza previa si no se provee config.
        batch_size: Tamaño de lote si no se provee config.
        write_postgres: Habilita persistencia PostgreSQL si no se provee config.
        reset_database: Limpia las tablas cargadas en PostgreSQL si no se provee config.

    Returns:
        int: Código de salida (0 para éxito, distinto de 0 en caso de error).
    """
    if config is None:
        seed = seed_value if seed_value is not None else 42
        config = SeedConfig(
            mode=mode,
            seed=seed,
            defect_rate=defect_rate,
            reset=reset,
            batch_size=batch_size,
            write_postgres=write_postgres,
            reset_database=reset_database,
        )

    try:
        logger.info("Iniciando proceso de seeding de AgroSense Café...")
        logger.info(
            "Configuración activa: mode=%s, seed=%d, defect_rate=%.2f, reset_memory=%s, "
            "write_postgres=%s, reset_database=%s, batch_size=%d",
            config.mode,
            config.seed,
            config.defect_rate,
            config.reset,
            config.write_postgres,
            config.reset_database,
            config.batch_size,
        )

        if config.reset_database and not config.write_postgres:
            raise ValueError("--reset-database requiere --write-postgres.")

        # 1. Asegurar estado pseudoaleatorio determinista con la semilla configurada
        set_reproducible_state(config.seed)

        # 2. Generación determinista de entidades sintéticas con integración de Faker
        faker_gen = AgroSenseFakerGenerator(seed=config.seed)
        dataset = faker_gen.generate_all(mode=config.mode)
        database_dataset = build_database_dataset(dataset)
        farms_count = len(dataset.get("farms", []))
        logger.info(
            "Dataset sintético generado con Faker: %d fincas, %d productores, %d sensores.",
            farms_count,
            len(dataset.get("producers", [])),
            len(dataset.get("iot_sensors", [])),
        )

        # 3. Motor de Idempotencia UPSERT y preparación de sentencias SQL
        engine = UpsertEngine(batch_size=config.batch_size)

        if config.reset:
            logger.info("Modo --reset activo: reiniciando el almacén simulado en memoria.")
            reset_database_state()

        # Preserve the full in-memory simulator; only SQL/database writes are projected
        # onto the current ORM contract.
        engine.apply_dataset_upsert(dataset)

        sql_statements = engine.build_all_upsert_statements(database_dataset)
        total_stmts = sum(len(stmts) for stmts in sql_statements.values())
        logger.info(
            "Sentencias UPSERT (ON CONFLICT) en 5 niveles topológicos: %d en %d tablas.",
            total_stmts,
            len(sql_statements),
        )

        # 4. Certificación estricta de idempotencia y verificación de no-inflación de filas (CT-06)
        idempotency_report = engine.verify_idempotency(dataset)
        if not idempotency_report["is_idempotent"] or idempotency_report["row_inflation_detected"]:
            logger.error("Fallo crítico: Violación de idempotencia detectada en la verificación.")
            return 1

        logger.info(
            "Certificación CT-06 aprobada: 0 inflación de filas y 0 duplicados en %d tablas.",
            idempotency_report["tables_tested"],
        )

        if config.write_postgres:
            database_url = os.getenv("AGROSENSE_DATABASE_URL")
            if not database_url:
                raise ValueError("--write-postgres requiere configurar AGROSENSE_DATABASE_URL.")
            from .postgres import write_dataset_to_postgres

            written_rows = write_dataset_to_postgres(
                database_dataset,
                database_url,
                engine=engine,
                reset_database=config.reset_database,
            )
            logger.info(
                "Persistencia PostgreSQL confirmada: %s",
                ", ".join(f"{table}={count}" for table, count in written_rows.items()),
            )
        else:
            logger.info(
                "Modo simulación: no se escribió en PostgreSQL. "
                "Use --write-postgres para persistir explícitamente."
            )

        # 5. Geometrías espaciales de muestra para diagnóstico CLI
        sample_data, reserve_data = generate_spatial_seed_records(
            generate_sample_seed_records(count=min(5, farms_count)), seed=config.seed
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

__all__ = [
    "SeedConfig",
    "build_parser",
    "calculate_database_checksum",
    "get_database_row_counts",
    "get_database_state",
    "main",
    "parse_args",
    "reset_database_state",
    "run_seed",
    "set_reproducible_state",
    "validate_defect_rate",
]
