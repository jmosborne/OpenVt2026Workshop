"""Validated run parameters for the OpenVT 2026 cell-sorting model.

Environment variables are used because they work in both Player and the
headless ``cc3d.run_script`` runner.  The defaults are a short development
run of the two-clump/random-mixture experiment.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping, Optional


@dataclass(frozen=True)
class RunProfile:
    name: str
    cell_count: int
    rows: int
    columns: int
    lattice_x: int
    lattice_y: int
    final_mcs: int


@dataclass(frozen=True)
class ContactRegime:
    """Symmetric contact energies J(type 1, type 2).

    Lower J denotes a more favourable interface.  ``core_type`` and
    ``shell_type`` are set only where the regime predicts engulfment.
    """

    name: str
    j_aa: float
    j_bb: float
    j_ab: float
    j_a_medium: float
    j_b_medium: float
    fluctuation_a: float
    fluctuation_b: float
    core_type: Optional[str] = None
    shell_type: Optional[str] = None


@dataclass(frozen=True)
class ModelConfig:
    profile: RunProfile
    regime: ContactRegime
    pattern: str
    seed: int
    sim_id: str
    output_dir: Optional[Path]
    fluctuation_a: float = 10.0
    fluctuation_b: float = 10.0
    target_volume: float = 25.0
    lambda_volume: float = 2.0
    centre_spacing: float = 5.4
    initial_radius: float = 3.2

    @property
    def export_interval(self) -> int:
        return self.profile.final_mcs // 100

    @property
    def export_times(self) -> tuple[int, ...]:
        interval = self.export_interval
        return tuple(range(0, self.profile.final_mcs + 1, interval))


PROFILES = {
    "development": RunProfile(
        name="development",
        cell_count=100,
        rows=10,
        columns=10,
        lattice_x=96,
        lattice_y=96,
        final_mcs=50_000,
    ),
    "production": RunProfile(
        name="production",
        cell_count=400,
        rows=20,
        columns=20,
        lattice_x=160,
        lattice_y=160,
        final_mcs=100_000,
    ),
}


REGIMES = {
    # Strongly unfavourable A-B interfaces drive like-with-like sorting.
    "two_clumps": ContactRegime(
        name="two_clumps",
        j_aa=8.0,
        j_bb=8.0,
        # Positive gamma(A,B)=16 drives demixing while J(A,B)<J(A,M)+J(B,M)
        # keeps both compact domains in one aggregate during coarsening.
        j_ab=24.0,
        j_a_medium=18.0,
        j_b_medium=18.0,
        fluctuation_a=10.0,
        fluctuation_b=10.0,
    ),
    # A-B interfaces are the most favourable, promoting alternation/mixing.
    "mixing": ContactRegime(
        name="mixing",
        j_aa=16.0,
        j_bb=16.0,
        j_ab=4.0,
        j_a_medium=18.0,
        j_b_medium=18.0,
        fluctuation_a=10.0,
        fluctuation_b=10.0,
    ),
    # A has the larger effective cell-medium surface tension and forms the
    # core; B preferentially occupies the outer shell.
    "engulfment": ContactRegime(
        name="engulfment",
        j_aa=8.0,
        j_bb=12.0,
        # Gives gamma(A,B)=6: enough to demix the core while preserving the
        # complete-wetting inequality gamma(A,M) > gamma(A,B)+gamma(B,M).
        j_ab=16.0,
        j_a_medium=24.0,
        j_b_medium=14.0,
        # Calibrated isolated-cell amplitudes equalize mobility despite the
        # different A-Medium and B-Medium contact energies.
        fluctuation_a=13.0,
        fluctuation_b=7.8,
        core_type="A",
        shell_type="B",
    ),
}


PATTERNS = frozenset({"random", "block"})


def _choice(env: Mapping[str, str], key: str, choices: Mapping | set | frozenset, default: str) -> str:
    value = env.get(key, default).strip().lower()
    if value not in choices:
        allowed = ", ".join(sorted(choices))
        raise ValueError(f"{key} must be one of: {allowed}; got {value!r}")
    return value


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
        raise ValueError(f"{key} must be a number; got {raw!r}") from exc


def load_config(env: Mapping[str, str] = os.environ) -> ModelConfig:
    profile_name = _choice(env, "OPENVT_PROFILE", PROFILES, "development")
    regime_name = _choice(env, "OPENVT_REGIME", REGIMES, "two_clumps")
    pattern = _choice(env, "OPENVT_PATTERN", PATTERNS, "random")
    seed = _integer(env, "OPENVT_SEED", 1)

    base_profile = PROFILES[profile_name]
    final_mcs = _integer(env, "OPENVT_FINAL_MCS", base_profile.final_mcs)
    if final_mcs <= 0 or final_mcs % 100:
        raise ValueError("OPENVT_FINAL_MCS must be positive and divisible by 100")
    profile = RunProfile(
        name=base_profile.name,
        cell_count=base_profile.cell_count,
        rows=base_profile.rows,
        columns=base_profile.columns,
        lattice_x=base_profile.lattice_x,
        lattice_y=base_profile.lattice_y,
        final_mcs=final_mcs,
    )

    default_sim_id = f"{profile_name}_{regime_name}_{pattern}_seed{seed}"
    sim_id = env.get("OPENVT_SIM_ID", default_sim_id).strip()
    if not sim_id or any(character in sim_id for character in ",\r\n"):
        raise ValueError("OPENVT_SIM_ID must be non-empty and contain no comma or newline")

    raw_output_dir = env.get("OPENVT_OUTPUT_DIR", "").strip()
    output_dir = Path(raw_output_dir).expanduser().resolve() if raw_output_dir else None

    regime = REGIMES[regime_name]
    if "OPENVT_TEMPERATURE" in env:
        scalar_amplitude = _number(env, "OPENVT_TEMPERATURE", 10.0)
        fluctuation_a = scalar_amplitude
        fluctuation_b = scalar_amplitude
    else:
        fluctuation_a = _number(env, "OPENVT_FLUCTUATION_A", regime.fluctuation_a)
        fluctuation_b = _number(env, "OPENVT_FLUCTUATION_B", regime.fluctuation_b)

    config = ModelConfig(
        profile=profile,
        regime=regime,
        pattern=pattern,
        seed=seed,
        sim_id=sim_id,
        output_dir=output_dir,
        fluctuation_a=fluctuation_a,
        fluctuation_b=fluctuation_b,
    )
    validate_config(config)
    return config


def validate_config(config: ModelConfig) -> None:
    profile = config.profile
    if profile.rows * profile.columns != profile.cell_count:
        raise ValueError("profile rows*columns must equal cell_count")
    if profile.cell_count % 2:
        raise ValueError("cell_count must be even for an exact 50:50 mixture")
    if len(config.export_times) != 101:
        raise ValueError("export schedule must contain exactly 101 time points")
    if config.export_times[0] != 0 or config.export_times[-1] != profile.final_mcs:
        raise ValueError("export schedule must include MCS 0 and final MCS")
    if config.fluctuation_a < 0 or config.fluctuation_b < 0:
        raise ValueError("Potts fluctuation amplitudes cannot be negative")
    if config.target_volume <= 0 or config.lambda_volume <= 0:
        raise ValueError("volume parameters must be positive")
