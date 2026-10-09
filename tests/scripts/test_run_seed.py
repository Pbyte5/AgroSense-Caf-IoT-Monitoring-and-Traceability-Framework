"""Unit tests for the seed CLI runner and argument parser."""

import argparse

import pytest

from scripts.seed.run_seed import (
    SeedConfig,
    build_parser,
    parse_args,
    run_seed,
    validate_defect_rate,
)


def test_default_cli_arguments():
    """Verify default values match project specifications."""
    config = parse_args([])
    assert config.mode == "dev"
    assert config.seed == 42
    assert config.defect_rate == 0.05
    assert config.reset is False


def test_custom_cli_arguments():
    """Verify customized CLI flags are properly parsed into SeedConfig."""
    args = ["--mode", "prod", "--seed", "100", "--defect-rate", "0.15", "--reset"]
    config = parse_args(args)
    assert config.mode == "prod"
    assert config.seed == 100
    assert config.defect_rate == 0.15
    assert config.reset is True


def test_invalid_mode_choice():
    """Verify that unsupported mode arguments raise a parser error."""
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--mode", "staging"])


def test_invalid_defect_rate_out_of_range():
    """Verify that defect rates outside [0.0, 1.0] raise validation error."""
    with pytest.raises(argparse.ArgumentTypeError):
        validate_defect_rate("-0.1")

    with pytest.raises(argparse.ArgumentTypeError):
        validate_defect_rate("1.5")


def test_invalid_defect_rate_non_float():
    """Verify that non-numeric defect rate raises validation error."""
    with pytest.raises(argparse.ArgumentTypeError):
        validate_defect_rate("invalid")


def test_run_seed_execution():
    """Verify that run_seed successfully returns exit code 0."""
    config = SeedConfig(mode="dev", seed=42, defect_rate=0.05, reset=False)
    exit_code = run_seed(config)
    assert exit_code == 0
