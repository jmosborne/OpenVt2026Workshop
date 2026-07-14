"""Environment-driven parameters for isolated-cell motility calibration."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping


@dataclass(frozen=True)
class CalibrationConfig:
    condition: str
    seed: int
    temperature: float
    j_medium: float
    burn_in_mcs: int
    duration_mcs: int
    sample_interval_mcs: int
    lattice_size: int = 96
    target_volume: float = 25.0
    lambda_volume: float = 2.0

    @property
    def total_steps(self) -> int:
        # CC3D calls step(mcs) for 0..Steps-1. The extra endpoint allows an
        # observation at burn_in+duration after exactly duration sampled MCS.
        return self.burn_in_mcs + self.duration_mcs + 1

    @property
    def expected_samples(self) -> int:
        return self.duration_mcs // self.sample_interval_mcs + 1


def _integer(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key, str(default)).strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{key} must be an integer; got {raw!r}") from exc


def _number(env: Mapping[str, str], key: str, default: float) -> float:
    raw = env.get(key, str(default)).strip()
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{key} must be numeric; got {raw!r}") from exc


def load_config(env: Mapping[str, str] = os.environ) -> CalibrationConfig:
    config = CalibrationConfig(
        condition=env.get("CALIB_CONDITION", "T10_J18").strip(),
        seed=_integer(env, "CALIB_SEED", 1),
        temperature=_number(env, "CALIB_TEMPERATURE", 10.0),
        j_medium=_number(env, "CALIB_J_MEDIUM", 18.0),
        burn_in_mcs=_integer(env, "CALIB_BURN_IN_MCS", 1_000),
        duration_mcs=_integer(env, "CALIB_DURATION_MCS", 5_000),
        sample_interval_mcs=_integer(env, "CALIB_SAMPLE_INTERVAL_MCS", 25),
        lattice_size=_integer(env, "CALIB_LATTICE_SIZE", 96),
    )
    if not config.condition or any(c in config.condition for c in ",\r\n"):
        raise ValueError("CALIB_CONDITION must be non-empty and contain no comma/newline")
    if config.temperature < 0 or config.j_medium < 0:
        raise ValueError("temperature and contact energy must be non-negative")
    if config.burn_in_mcs < 0 or config.duration_mcs <= 0 or config.sample_interval_mcs <= 0:
        raise ValueError("burn-in must be non-negative; duration and interval must be positive")
    if config.duration_mcs % config.sample_interval_mcs:
        raise ValueError("CALIB_DURATION_MCS must be divisible by CALIB_SAMPLE_INTERVAL_MCS")
    if config.lattice_size < 32:
        raise ValueError("CALIB_LATTICE_SIZE must be at least 32")
    return config
