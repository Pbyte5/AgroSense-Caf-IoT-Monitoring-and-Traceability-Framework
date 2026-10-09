"""AgroSense Café — Reproducible and Idempotent Data Seed Script.

CLI script supporting deterministic seed parameters, modes, defect rates,
and reset operations for PostgreSQL and storage layers.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass

logger = logging.getLogger("agrosense.seed")


@dataclass(frozen=True)
class SeedConfig:
    """Configuration options for data seeding execution."""

    mode: str
    seed: int
    defect_rate: float
    reset: bool = False


def validate_defect_rate(val: str) -> float:
    """Validate that defect-rate is a float between 0.0 and 1.0."""
    try:
        fval = float(val)
    except ValueError as err:
        raise argparse.ArgumentTypeError(f"Defect rate must be a float, got {val!r}") from err

    if not 0.0 <= fval <= 1.0:
        raise argparse.ArgumentTypeError(f"Defect rate must be between 0.0 and 1.0, got {fval}")
    return fval


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser for run_seed.py."""
    parser = argparse.ArgumentParser(
        prog="run_seed.py",
        description=(
            "AgroSense Café - Reproducible and Idempotent Synthetic Data Seed Runner. "
            "Populates PostgreSQL and storage layers with domain data."
        ),
    )

    parser.add_argument(
        "--mode",
        choices=["dev", "prod"],
        default="dev",
        help=(
            "Dataset scale profile: 'dev' (lightweight fast local) "
            "or 'prod' (full volume). Default: dev."
        ),
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Integer seed for PRNG to ensure deterministic generation. Default: 42.",
    )

    parser.add_argument(
        "--defect-rate",
        type=validate_defect_rate,
        default=0.05,
        dest="defect_rate",
        help="Ratio of synthetic data quality defects to inject (0.0 to 1.0). Default: 0.05.",
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        default=False,
        help="Wipe operational tables and reset sequences before seeding (atomic TRUNCATE).",
    )

    return parser


def parse_args(args: Sequence[str] | None = None) -> SeedConfig:
    """Parse and validate command line arguments into a SeedConfig."""
    parser = build_parser()
    parsed = parser.parse_args(args)
    return SeedConfig(
        mode=parsed.mode,
        seed=parsed.seed,
        defect_rate=parsed.defect_rate,
        reset=parsed.reset,
    )


def run_seed(config: SeedConfig) -> int:
    """Execute the data seeding process with the provided configuration."""
    logger.info("Initializing AgroSense seed process...")
    logger.info(
        "Configuration: mode=%s, seed=%d, defect_rate=%.2f, reset=%s",
        config.mode,
        config.seed,
        config.defect_rate,
        config.reset,
    )

    # Core generation logic will be hooked in subsequent modules
    logger.info("Seed execution finished successfully.")
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entry point for run_seed."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    )
    config = parse_args(argv)
    exit_code = run_seed(config)
    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
