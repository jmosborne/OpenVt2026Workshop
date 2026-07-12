#!/usr/bin/env python3
"""Validate an OpenVT portal CSV and its cell-count invariants."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


HEADER = ["simID", "time", "cellID", "cellType", "x", "y"]
TYPE_LABELS = {"A": "A", "B": "B", "0": "A", "1": "B"}


def validate(path: Path, expected_cells: int, expected_a: int | None = None, expected_b: int | None = None) -> dict[str, object]:
    expected_a = expected_cells // 2 if expected_a is None else expected_a
    expected_b = expected_cells // 2 if expected_b is None else expected_b
    by_time: dict[float, list[dict[str, str]]] = defaultdict(list)
    sim_ids: set[str] = set()

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != HEADER:
            raise ValueError(f"Expected exact header {','.join(HEADER)}; found {reader.fieldnames}")
        for line_number, row in enumerate(reader, start=2):
            try:
                time = float(row["time"])
                x = float(row["x"])
                y = float(row["y"])
            except ValueError as error:
                raise ValueError(f"Non-numeric time/coordinate at line {line_number}") from error
            if not all(math.isfinite(value) for value in (time, x, y)):
                raise ValueError(f"Non-finite time/coordinate at line {line_number}")
            if row["cellType"] not in TYPE_LABELS:
                raise ValueError(f"Unexpected cell type {row['cellType']!r} at line {line_number}")
            by_time[time].append(row)
            sim_ids.add(row["simID"])

    times = sorted(by_time)
    if len(times) != 101:
        raise ValueError(f"Expected 101 time points; found {len(times)}")
    if len(sim_ids) != 1:
        raise ValueError(f"Expected one simID; found {sorted(sim_ids)}")
    intervals = [right - left for left, right in zip(times, times[1:])]
    interval_tolerance = max(1e-9, abs(intervals[0]) * 1e-7) if intervals else 1e-9
    if intervals and not all(math.isclose(value, intervals[0], rel_tol=1e-9, abs_tol=interval_tolerance) for value in intervals):
        raise ValueError("Sample times are not evenly spaced")

    reference_ids: set[str] | None = None
    for time in times:
        rows = by_time[time]
        ids = {row["cellID"] for row in rows}
        type_counts = Counter(TYPE_LABELS[row["cellType"]] for row in rows)
        if len(rows) != expected_cells or len(ids) != expected_cells:
            raise ValueError(f"At time {time:g}: expected {expected_cells} unique cells; found {len(rows)} rows/{len(ids)} IDs")
        if type_counts != Counter({"A": expected_a, "B": expected_b}):
            raise ValueError(f"At time {time:g}: expected A={expected_a}, B={expected_b}; found {dict(type_counts)}")
        if reference_ids is None:
            reference_ids = ids
        elif ids != reference_ids:
            raise ValueError(f"Cell ID set changed at time {time:g}")

    return {
        "status": "valid",
        "path": str(path.resolve()),
        "sim_id": next(iter(sim_ids)),
        "rows": sum(len(rows) for rows in by_time.values()),
        "time_points": len(times),
        "start_time": times[0],
        "end_time": times[-1],
        "sample_interval": intervals[0] if intervals else 0,
        "cells_per_time": expected_cells,
        "cell_type_counts_per_time": {"A": expected_a, "B": expected_b},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--cells", type=int, required=True)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    result = validate(args.csv, args.cells)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_output:
        args.json_output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
