#!/usr/bin/env python3
"""Convert a Morpheus per-cell logger CSV to the OpenVT portal schema."""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path


SOURCE_COLUMNS = (
    "time",
    "cell.id",
    "cell.type",
    "cell.center.x",
    "cell.center.y",
)
OUTPUT_COLUMNS = ("simID", "time", "cellID", "cellType", "x", "y")


class ExportError(ValueError):
    """Raised when logger data do not satisfy the portal contract."""


def positive_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite number greater than zero")
    return number


def predicted_cell_diameter(target_volume: float) -> float:
    if not math.isfinite(target_volume) or target_volume <= 0:
        raise ExportError("target volume must be finite and greater than zero")
    return 2.0 * (3.0 * target_volume / (4.0 * math.pi)) ** (1.0 / 3.0)


def _integer(value: str, label: str) -> int:
    number = float(value)
    if not math.isfinite(number) or not math.isclose(number, round(number), abs_tol=1e-9):
        raise ExportError(f"{label} must be integer-valued, got {value!r}")
    return int(round(number))


def convert(raw_log: Path, output_csv: Path, expected_cells: int, target_volume: float) -> None:
    if expected_cells not in (100, 400):
        raise ExportError("expected cells must be 100 or 400")

    with raw_log.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        missing = [name for name in SOURCE_COLUMNS if name not in (reader.fieldnames or ())]
        if missing:
            raise ExportError(f"missing source columns: {', '.join(missing)}")
        raw_rows = list(reader)

    if not raw_rows:
        raise ExportError("raw logger file is empty")

    by_time: dict[int, list[tuple[int, int, float, float]]] = defaultdict(list)
    all_types: set[int] = set()
    for line_number, row in enumerate(raw_rows, start=2):
        time = _integer(row["time"], f"time on line {line_number}")
        cell_id = _integer(row["cell.id"], f"cell.id on line {line_number}")
        cell_type = _integer(row["cell.type"], f"cell.type on line {line_number}")
        x = float(row["cell.center.x"])
        y = float(row["cell.center.y"])
        if not math.isfinite(x) or not math.isfinite(y):
            raise ExportError(f"coordinates must be finite on line {line_number}")
        by_time[time].append((cell_id, cell_type, x, y))
        all_types.add(cell_type)

    times = sorted(by_time)
    if len(times) != 101:
        raise ExportError(f"expected 101 time points, found {len(times)}")
    intervals = {later - earlier for earlier, later in zip(times, times[1:])}
    if len(intervals) != 1 or next(iter(intervals)) <= 0:
        raise ExportError("time points must be evenly spaced and increasing")
    if times[0] != 0:
        raise ExportError(f"first time point must be 0, found {times[0]}")
    if len(all_types) != 2:
        raise ExportError(f"expected exactly two cell types, found {len(all_types)}")

    reference_ids: set[int] | None = None
    for time in times:
        rows = by_time[time]
        if len(rows) != expected_cells:
            raise ExportError(
                f"time {time} contains {len(rows)} rows; expected {expected_cells}"
            )
        ids = {row[0] for row in rows}
        if len(ids) != expected_cells:
            raise ExportError(f"time {time} contains duplicate cell IDs")
        if reference_ids is None:
            reference_ids = ids
        elif ids != reference_ids:
            raise ExportError(f"cell ID set changed at time {time}")

    diameter = predicted_cell_diameter(target_volume)
    type_map = {source_type: portal_type for portal_type, source_type in enumerate(sorted(all_types))}
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=OUTPUT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for time in times:
            for cell_id, cell_type, x, y in sorted(by_time[time], key=lambda row: row[0]):
                writer.writerow(
                    {
                        "simID": 0,
                        "time": time,
                        "cellID": cell_id,
                        "cellType": type_map[cell_type],
                        "x": f"{x / diameter:.10g}",
                        "y": f"{y / diameter:.10g}",
                    }
                )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_log", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("--expected-cells", required=True, type=int, choices=(100, 400))
    parser.add_argument("--target-volume", required=True, type=positive_float)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        convert(args.raw_log, args.output_csv, args.expected_cells, args.target_volume)
    except (OSError, ExportError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error


if __name__ == "__main__":
    main()
