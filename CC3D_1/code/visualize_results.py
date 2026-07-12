#!/usr/bin/env python3
"""Visualize OpenVT cell-centre CSV output from the three parameter regimes."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt


COLORS = {"A": "#0072B2", "B": "#D55E00"}
REGIME_LABELS = {
    "two_clumps": "Two compact clumps",
    "mixing": "Heterotypic mixing",
    "engulfment": "Engulfment (A core, B shell)",
}


def read_positions(path: Path) -> dict[int, list[dict[str, float | str]]]:
    snapshots: dict[int, list[dict[str, float | str]]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        expected = ["simID", "time", "cellID", "cellType", "x", "y"]
        if reader.fieldnames != expected:
            raise ValueError(f"{path} has header {reader.fieldnames}, expected {expected}")
        for row in reader:
            time = int(row["time"])
            snapshots.setdefault(time, []).append(
                {
                    "type": row["cellType"],
                    "x": float(row["x"]),
                    "y": float(row["y"]),
                }
            )
    if len(snapshots) != 101:
        raise ValueError(f"{path} contains {len(snapshots)} time points, expected 101")
    return snapshots


def neighbour_fraction(cells, same_type: bool, neighbours: int = 6) -> float:
    matches = 0
    comparisons = 0
    for index, cell in enumerate(cells):
        nearest = sorted(
            (
                math.hypot(cell["x"] - other["x"], cell["y"] - other["y"]),
                other_index,
                other,
            )
            for other_index, other in enumerate(cells)
            if other_index != index
        )[:neighbours]
        for _, _, other in nearest:
            equal = cell["type"] == other["type"]
            matches += equal if same_type else not equal
            comparisons += 1
    return matches / comparisons


def mean_radii(cells) -> dict[str, float]:
    centre_x = sum(cell["x"] for cell in cells) / len(cells)
    centre_y = sum(cell["y"] for cell in cells) / len(cells)
    radii = {"A": [], "B": []}
    for cell in cells:
        radii[cell["type"]].append(
            math.hypot(cell["x"] - centre_x, cell["y"] - centre_y)
        )
    return {cell_type: sum(values) / len(values) for cell_type, values in radii.items()}


def plot_snapshots(results, output_path: Path) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(10, 13), constrained_layout=True)
    for row, regime in enumerate(("two_clumps", "mixing", "engulfment")):
        snapshots = results[regime]
        times = sorted(snapshots)
        all_cells = snapshots[times[0]] + snapshots[times[-1]]
        x_values = [cell["x"] for cell in all_cells]
        y_values = [cell["y"] for cell in all_cells]
        padding = 6
        limits = (
            min(x_values) - padding,
            max(x_values) + padding,
            min(y_values) - padding,
            max(y_values) + padding,
        )
        for column, time in enumerate((times[0], times[-1])):
            axis = axes[row, column]
            cells = snapshots[time]
            for cell_type in ("A", "B"):
                selected = [cell for cell in cells if cell["type"] == cell_type]
                axis.scatter(
                    [cell["x"] for cell in selected],
                    [cell["y"] for cell in selected],
                    s=72,
                    color=COLORS[cell_type],
                    edgecolor="white",
                    linewidth=0.45,
                    label=f"Type {cell_type}",
                    alpha=0.95,
                )
            axis.set(
                xlim=limits[:2],
                ylim=limits[2:],
                aspect="equal",
                xlabel="x (lattice units)",
                ylabel="y (lattice units)",
            )
            axis.grid(alpha=0.15)
            state = "Initial" if column == 0 else "Final"
            axis.set_title(f"{REGIME_LABELS[regime]}\n{state}: MCS {time:,}")
            if row == 0 and column == 1:
                axis.legend(frameon=False, loc="upper right")
    fig.suptitle(
        "OpenVT 2026 cell-sorting development runs\n"
        "Cell-centre trajectories under differential contact energies",
        fontsize=16,
    )
    fig.text(
        0.5,
        -0.005,
        "Markers show exported centres of mass; marker size is illustrative, not cell area.",
        ha="center",
        fontsize=9,
        color="#555555",
    )
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_dynamics(results, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), constrained_layout=True)

    clump_times = sorted(results["two_clumps"])
    clump_values = [
        neighbour_fraction(results["two_clumps"][time], same_type=True)
        for time in clump_times
    ]
    axes[0].plot(clump_times, clump_values, color="#009E73", linewidth=2.2)
    axes[0].set(
        title="Two-clump sorting",
        xlabel="MCS",
        ylabel="Same-type fraction among 6 nearest",
        ylim=(0, 1.03),
    )

    mixing_times = sorted(results["mixing"])
    mixing_values = [
        neighbour_fraction(results["mixing"][time], same_type=False)
        for time in mixing_times
    ]
    axes[1].plot(mixing_times, mixing_values, color="#CC79A7", linewidth=2.2)
    axes[1].set(
        title="Heterotypic mixing",
        xlabel="MCS",
        ylabel="Opposite-type fraction among 6 nearest",
        ylim=(0, 1.03),
    )

    engulfment_times = sorted(results["engulfment"])
    radius_series = [mean_radii(results["engulfment"][time]) for time in engulfment_times]
    for cell_type in ("A", "B"):
        axes[2].plot(
            engulfment_times,
            [values[cell_type] for values in radius_series],
            color=COLORS[cell_type],
            linewidth=2.2,
            label=f"Type {cell_type}",
        )
    axes[2].set(
        title="Engulfment",
        xlabel="MCS",
        ylabel="Mean radius from cluster centre",
    )
    axes[2].legend(frameon=False)

    for axis in axes:
        axis.grid(alpha=0.2)
        axis.spines[["top", "right"]].set_visible(False)
        axis.ticklabel_format(axis="x", style="plain")
    fig.suptitle("Quantitative organization over time", fontsize=16)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--two-clumps", type=Path, required=True)
    parser.add_argument("--mixing", type=Path, required=True)
    parser.add_argument("--engulfment", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = {
        "two_clumps": read_positions(args.two_clumps),
        "mixing": read_positions(args.mixing),
        "engulfment": read_positions(args.engulfment),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    plot_snapshots(results, args.output_dir / "cell_sorting_snapshots.png")
    plot_dynamics(results, args.output_dir / "cell_sorting_dynamics.png")


if __name__ == "__main__":
    main()
