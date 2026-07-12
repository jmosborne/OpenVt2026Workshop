#!/usr/bin/env python3
"""Estimate isolated-cell MSD slopes and MCS-to-reference-time conversion."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


CONDITION_METADATA = {
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


def read_trajectory(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    mcs = np.array([int(row["mcs"]) for row in rows], dtype=float)
    xy = np.array([[float(row["x"]), float(row["y"])] for row in rows])
    volume = np.array([float(row["volume"]) for row in rows])
    return mcs, xy, volume


def trajectory_tamsd(xy: np.ndarray, max_lag_index: int, diameter: float) -> np.ndarray:
    values = []
    for lag in range(1, max_lag_index + 1):
        displacement = xy[lag:] - xy[:-lag]
        values.append(np.mean(np.sum(displacement * displacement, axis=1)) / diameter**2)
    return np.array(values)


def fit_through_origin(lags: np.ndarray, msd: np.ndarray, fit_min: int, fit_max: int):
    selected = (lags >= fit_min) & (lags <= fit_max)
    x = lags[selected]
    y = msd[selected]
    slope = float(np.dot(x, y) / np.dot(x, x))
    fitted = slope * x
    residual = float(np.sum((y - fitted) ** 2))
    total = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - residual / total if total else 1.0
    return slope, r_squared


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cell-diameter", type=float, default=5.4)
    parser.add_argument("--fit-min-mcs", type=int, default=100)
    parser.add_argument("--fit-max-mcs", type=int, default=1_000)
    parser.add_argument(
        "--analysis-max-mcs",
        type=int,
        default=2_000,
        help="discard later positions so boundary encounters cannot bias TAMSD",
    )
    parser.add_argument("--bootstrap", type=int, default=1_000)
    parser.add_argument("--lattice-size", type=int, default=96)
    parser.add_argument(
        "--conditions", nargs="+", choices=sorted(CONDITION_METADATA), default=None
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.input_root = args.input_root.expanduser().resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20260712)
    summaries = []
    curves = {}

    selected_conditions = args.conditions or list(CONDITION_METADATA)
    for condition in selected_conditions:
        temperature, j_medium = CONDITION_METADATA[condition]
        paths = sorted((args.input_root / condition).glob("seed_*/calibration_positions.csv"))
        if len(paths) < 2:
            raise ValueError(f"need at least two trajectories for {condition}, found {len(paths)}")
        trajectories = [read_trajectory(path) for path in paths]
        trajectories = [
            (mcs[mcs <= args.analysis_max_mcs], xy[mcs <= args.analysis_max_mcs], volume[mcs <= args.analysis_max_mcs])
            for mcs, xy, volume in trajectories
        ]
        reference_mcs = trajectories[0][0]
        if any(not np.array_equal(mcs, reference_mcs) for mcs, _, _ in trajectories):
            raise ValueError(f"inconsistent sample times for {condition}")
        interval = int(reference_mcs[1] - reference_mcs[0])
        max_lag_index = args.fit_max_mcs // interval
        lags = np.arange(1, max_lag_index + 1) * interval
        per_trajectory = np.array(
            [trajectory_tamsd(xy, max_lag_index, args.cell_diameter) for _, xy, _ in trajectories]
        )
        mean_msd = np.mean(per_trajectory, axis=0)
        slope, r_squared = fit_through_origin(
            lags, mean_msd, args.fit_min_mcs, args.fit_max_mcs
        )

        bootstrap_slopes = []
        for _ in range(args.bootstrap):
            indices = rng.integers(0, len(paths), len(paths))
            sample_curve = np.mean(per_trajectory[indices], axis=0)
            bootstrap_slopes.append(
                fit_through_origin(
                    lags, sample_curve, args.fit_min_mcs, args.fit_max_mcs
                )[0]
            )
        low, high = np.quantile(bootstrap_slopes, [0.025, 0.975])
        volumes = np.concatenate([volume for _, _, volume in trajectories])
        all_xy = np.concatenate([xy for _, xy, _ in trajectories])
        min_boundary_distance = float(
            np.min(
                np.column_stack(
                    [
                        all_xy[:, 0],
                        all_xy[:, 1],
                        args.lattice_size - 1 - all_xy[:, 0],
                        args.lattice_size - 1 - all_xy[:, 1],
                    ]
                )
            )
        )
        summaries.append(
            {
                "condition": condition,
                "temperature": temperature,
                "jMedium": j_medium,
                "replicates": len(paths),
                "fitMinMCS": args.fit_min_mcs,
                "fitMaxMCS": args.fit_max_mcs,
                "msdSlopeCD2PerMCS": slope,
                "slopeCI95Low": low,
                "slopeCI95High": high,
                "mcsPerCD2": 1.0 / slope,
                "referenceTimeUnitsPerMCS": 100.0 * slope,
                "fitR2": r_squared,
                "meanVolume": float(np.mean(volumes)),
                "equivalentDiameter": float(2.0 * np.sqrt(np.mean(volumes) / np.pi)),
                "minBoundaryDistance": min_boundary_distance,
            }
        )
        curves[condition] = (lags, mean_msd, slope)

    summary_path = args.output_dir / "motility_calibration_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)

    fig, axis = plt.subplots(figsize=(8, 5.5), constrained_layout=True)
    for condition, (lags, msd, slope) in curves.items():
        axis.plot(lags, msd, linewidth=2, marker="o", markersize=3, label=condition)
        axis.plot(lags, slope * lags, linestyle="--", linewidth=1, alpha=0.7)
    axis.set(
        xlabel="Lag (MCS)",
        ylabel="Time-averaged MSD (cell diameters²)",
        title="Isolated-cell Potts motility calibration",
    )
    axis.grid(alpha=0.2)
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(frameon=False, fontsize=8)
    fig.savefig(
        args.output_dir / "motility_calibration.png", dpi=220, bbox_inches="tight"
    )
    plt.close(fig)


if __name__ == "__main__":
    main()
