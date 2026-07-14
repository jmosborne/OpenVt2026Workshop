#!/usr/bin/env python3
"""Run replicated isolated-cell calibration conditions concurrently."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import os
from pathlib import Path
import subprocess


CONDITIONS = {
    "sorting_T20_J18": (20.0, 18.0),
    "mixing_T10_J18": (10.0, 18.0),
    "engulfment_A_T10_J24": (10.0, 24.0),
    "engulfment_B_T10_J14": (10.0, 14.0),
    "engulfment_A_T15_J24": (15.0, 24.0),
    "engulfment_B_T7_J14": (7.0, 14.0),
    "engulfment_A_T13_J24": (13.0, 24.0),
    "engulfment_B_T8_J14": (8.0, 14.0),
    "engulfment_B_T7p5_J14": (7.5, 14.0),
    "engulfment_B_T7p7_J14": (7.7, 14.0),
    "engulfment_B_T7p8_J14": (7.8, 14.0),
    "type_specific_T10_J18": (10.0, 18.0),
}


def run_one(args, condition: str, replicate: int) -> tuple[str, int, Path]:
    temperature, j_medium = CONDITIONS[condition]
    seed = args.first_seed + replicate
    output_dir = args.output_root / condition / f"seed_{seed}"
    output_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "CALIB_CONDITION": condition,
            "CALIB_SEED": str(seed),
            "CALIB_TEMPERATURE": str(temperature),
            "CALIB_J_MEDIUM": str(j_medium),
            "CALIB_BURN_IN_MCS": str(args.burn_in),
            "CALIB_DURATION_MCS": str(args.duration),
            "CALIB_SAMPLE_INTERVAL_MCS": str(args.interval),
            "CALIB_LATTICE_SIZE": str(args.lattice_size),
        }
    )
    command = [
        "/bin/bash",
        str(args.runner),
        "-i",
        str(args.project),
        "-o",
        str(output_dir),
        "--log-level",
        "WARNING",
    ]
    completed = subprocess.run(command, env=env, text=True, capture_output=True)
    (output_dir / "runner.log").write_text(
        completed.stdout + completed.stderr, encoding="utf-8"
    )
    csv_path = output_dir / "calibration_positions.csv"
    if completed.returncode != 0 or not csv_path.is_file():
        raise RuntimeError(
            f"{condition} seed {seed} failed (exit {completed.returncode}); "
            f"see {output_dir / 'runner.log'}"
        )
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected = args.duration // args.interval + 1
    if len(rows) != expected:
        raise RuntimeError(
            f"{condition} seed {seed}: expected {expected} rows, got {len(rows)}"
        )
    return condition, seed, csv_path


def parse_args():
    script_dir = Path(__file__).resolve().parent
    workspace = script_dir.parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runner",
        type=Path,
        default=workspace / "CompuCell3D" / "runScript.command",
    )
    parser.add_argument(
        "--project", type=Path, default=script_dir / "MotilityCalibration.cc3d"
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--replicates", type=int, default=12)
    parser.add_argument("--first-seed", type=int, default=1001)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--burn-in", type=int, default=1_000)
    parser.add_argument("--duration", type=int, default=5_000)
    parser.add_argument("--interval", type=int, default=25)
    parser.add_argument("--lattice-size", type=int, default=96)
    parser.add_argument(
        "--conditions", nargs="+", choices=sorted(CONDITIONS), default=None
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.runner = args.runner.expanduser().resolve()
    args.project = args.project.expanduser().resolve()
    args.output_root = args.output_root.expanduser().resolve()
    if not args.runner.is_file() or not os.access(args.runner, os.X_OK):
        raise ValueError(f"runner is not executable: {args.runner}")
    if args.replicates <= 1 or args.workers <= 0:
        raise ValueError("replicates must exceed 1 and workers must be positive")
    args.output_root.mkdir(parents=True, exist_ok=True)

    selected_conditions = args.conditions or list(CONDITIONS)
    jobs = [
        (condition, replicate)
        for condition in selected_conditions
        for replicate in range(args.replicates)
    ]
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(run_one, args, condition, replicate): (condition, replicate)
            for condition, replicate in jobs
        }
        for future in as_completed(futures):
            condition, seed, path = future.result()
            print(f"completed {condition} seed={seed}: {path}", flush=True)


if __name__ == "__main__":
    main()
