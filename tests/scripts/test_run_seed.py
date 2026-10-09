"""Unit tests for the seed CLI runner and argument parser."""

import argparse

import pytest

from scripts.seed.run_seed import (
    SeedConfig,
    build_parser,
    generate_sample_seed_records,
    main,
    parse_args,
    run_seed,
    set_reproducible_state,
    validate_defect_rate,
)


def test_default_cli_arguments():
    """Verify default values match project specifications."""
    config = parse_args([])
    assert config.mode == "dev"
    assert config.seed == 42
    assert config.defect_rate == 0.05
    assert config.reset is False


def test_env_var_fallbacks(monkeypatch):
    """Verify CLI defaults properly read environment variables."""
    monkeypatch.setenv("SEED_PROFILE", "prod")
    monkeypatch.setenv("SEED_RANDOM_STATE", "99")
    monkeypatch.setenv("SEED_DEFECT_GLOBAL_RATE", "0.20")

    config = parse_args([])
    assert config.mode == "prod"
    assert config.seed == 99
    assert config.defect_rate == 0.20


def test_env_var_invalid_fallbacks(monkeypatch):
    """Verify CLI handles invalid environment variables safely with defaults."""
    monkeypatch.setenv("SEED_PROFILE", "invalid_mode")
    monkeypatch.setenv("SEED_RANDOM_STATE", "not_an_int")
    monkeypatch.setenv("SEED_DEFECT_GLOBAL_RATE", "1.5")  # out of [0, 1]

    config = parse_args([])
    assert config.mode == "dev"
    assert config.seed == 42
    assert config.defect_rate == 0.05

    monkeypatch.setenv("SEED_DEFECT_GLOBAL_RATE", "invalid_text")
    config2 = parse_args([])
    assert config2.defect_rate == 0.05


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


def test_set_reproducible_state():
    """Verify that setting the reproducible state sets seeds without error."""
    set_reproducible_state(42)


def test_generate_sample_seed_records_determinism():
    """Verify that generating sample records with same seed yields identical results."""
    set_reproducible_state(42)
    sample_1 = generate_sample_seed_records(count=5)

    set_reproducible_state(42)
    sample_2 = generate_sample_seed_records(count=5)

    assert len(sample_1) == 5
    assert sample_1 == sample_2
    assert sample_1[0]["farm_code"] == "FIN-0001"
    assert sample_1[0]["farm_id"] == "7060dc2f-48eb-5db4-9a7d-47ac1b4b4ae9"


def test_run_seed_execution():
    """Verify that run_seed successfully returns exit code 0."""
    config = SeedConfig(mode="dev", seed=42, defect_rate=0.05, reset=False)
    exit_code = run_seed(config)
    assert exit_code == 0


def test_run_seed_exception_handling(monkeypatch):
    """Verify that run_seed catches exceptions and returns exit code 1."""
    config = SeedConfig(mode="dev", seed=42, defect_rate=0.05, reset=False)
    monkeypatch.setattr(
        "scripts.seed.run_seed.set_reproducible_state",
        lambda _: (_ for _ in ()).throw(RuntimeError("Simulated seed failure")),
    )
    exit_code = run_seed(config)
    assert exit_code == 1


def test_main_entrypoint():
    """Verify that main runs end-to-end without unhandled exceptions."""
    main([])


def test_main_entrypoint_failure(monkeypatch):
    """Verify that main raises SystemExit with non-zero code on failure."""
    monkeypatch.setattr("scripts.seed.run_seed.run_seed", lambda _: 1)
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 1
