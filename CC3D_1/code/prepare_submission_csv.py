#!/usr/bin/env python3
"""Convert one or more CC3D exports to the OpenVT upload convention.

Coordinates are divided by a supplied relaxed-cell diameter. Cell types and
IDs are converted to numeric 0/1 and 0-based values. By default the 101
snapshots are labelled with relative times 0..100 unless a calibrated
reference-time-per-MCS factor is supplied.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


HEADER = ["simID", "time", "cellID", "cellType", "x", "y"]
TYPE_IDS = {"A": 0, "B": 1}


def parse_run(value: str) -> tuple[str, Path]:
    try:
        sim_id, raw_path = value.split("=", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("run must be SIM_ID=/path/to/cell_positions.csv") from exc
    if not sim_id or any(character in sim_id for character in ",\r\n"):
        raise argparse.ArgumentTypeError("SIM_ID must be non-empty and contain no comma/newline")
    path = Path(raw_path).expanduser().resolve()
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"CSV does not exist: {path}")
    return sim_id, path


def read_and_validate(path: Path) -> tuple[list[int], dict[int, list[dict[str, str]]]]:
    snapshots: dict[int, list[dict[str, str]]] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != HEADER:
            raise ValueError(f"{path} has header {reader.fieldnames}, expected {HEADER}")
        for row in reader:
            time = int(row["time"])
            if row["cellType"] not in TYPE_IDS:
                raise ValueError(f"{path}: unknown cell type {row['cellType']!r}")
            x = float(row["x"])
            y = float(row["y"])
            if not math.isfinite(x) or not math.isfinite(y):
                raise ValueError(f"{path}: non-finite coordinate")
            snapshots.setdefault(time, []).append(row)

    times = sorted(snapshots)
    if len(times) != 101:
        raise ValueError(f"{path} has {len(times)} snapshots, expected 101")
    expected_count = len(snapshots[times[0]])
    if expected_count not in (100, 400):
        raise ValueError(f"{path} has {expected_count} cells, expected 100 or 400")

    reference_ids = {row["cellID"] for row in snapshots[times[0]]}
    for time in times:
        rows = snapshots[time]
        if len(rows) != expected_count or {row["cellID"] for row in rows} != reference_ids:
            raise ValueError(f"{path}: cell IDs/count changed at time {time}")
        counts = {cell_type: sum(row["cellType"] == cell_type for row in rows) for cell_type in TYPE_IDS}
        if counts != {"A": expected_count // 2, "B": expected_count // 2}:
            raise ValueError(f"{path}: type counts are not exactly 50:50 at time {time}: {counts}")
    return times, snapshots


def convert_run(
    writer,
    sim_id: str,
    path: Path,
    cell_diameter: float,
    time_units_per_mcs: float | None,
) -> int:
    times, snapshots = read_and_validate(path)
    original_ids = sorted(
        {row["cellID"] for row in snapshots[times[0]]}, key=lambda value: int(value)
    )
    output_ids = {original_id: index for index, original_id in enumerate(original_ids)}
    rows_written = 0
    for relative_time, source_time in enumerate(times):
        output_time = (
            f"{source_time * time_units_per_mcs:.8f}"
            if time_units_per_mcs is not None
            else relative_time
        )
        for row in sorted(snapshots[source_time], key=lambda value: int(value["cellID"])):
            writer.writerow(
                [
                    sim_id,
                    output_time,
                    output_ids[row["cellID"]],
                    TYPE_IDS[row["cellType"]],
                    f"{float(row['x']) / cell_diameter:.8f}",
                    f"{float(row['y']) / cell_diameter:.8f}",
                ]
            )
            rows_written += 1
    return rows_written


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run",
        action="append",
        required=True,
        type=parse_run,
        metavar="SIM_ID=CSV",
        help="repeat once per simulation",
    )
    parser.add_argument("--cell-diameter", type=float, default=5.4)
    parser.add_argument(
        "--time-units-per-mcs",
        type=float,
        default=None,
        help="calibrated reference time units per MCS; omit for relative 0..100 time",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.cell_diameter <= 0:
        raise ValueError("--cell-diameter must be positive")
    sim_ids = [sim_id for sim_id, _ in args.run]
    if len(sim_ids) != len(set(sim_ids)):
        raise ValueError("each --run must have a unique SIM_ID")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(HEADER)
        for sim_id, path in args.run:
            convert_run(
                writer,
                sim_id,
                path,
                args.cell_diameter,
                args.time_units_per_mcs,
            )


if __name__ == "__main__":
    main()
