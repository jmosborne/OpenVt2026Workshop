"""Pure geometry and type-assignment helpers for model initialization."""

from __future__ import annotations

import math
import random
from typing import Iterable, Sequence


Centre = tuple[float, float]
Pixel = tuple[int, int]


def hexagonal_centres(
    rows: int,
    columns: int,
    spacing: float,
    lattice_x: int,
    lattice_y: int,
) -> list[Centre]:
    """Return a centred triangular lattice (hexagonal packing) of centres."""
    if min(rows, columns, spacing, lattice_x, lattice_y) <= 0:
        raise ValueError("grid and lattice dimensions must be positive")

    row_spacing = math.sqrt(3.0) * spacing / 2.0
    raw = [
        (column * spacing + (row % 2) * spacing / 2.0, row * row_spacing)
        for row in range(rows)
        for column in range(columns)
    ]
    min_x = min(x for x, _ in raw)
    max_x = max(x for x, _ in raw)
    min_y = min(y for _, y in raw)
    max_y = max(y for _, y in raw)
    shift_x = (lattice_x - 1 - (max_x - min_x)) / 2.0 - min_x
    shift_y = (lattice_y - 1 - (max_y - min_y)) / 2.0 - min_y
    return [(x + shift_x, y + shift_y) for x, y in raw]


def disk_pixels(centre: Centre, radius: float, lattice_x: int, lattice_y: int) -> list[Pixel]:
    """Rasterize one circular seed cell around a (possibly fractional) centre."""
    cx, cy = centre
    radius_squared = radius * radius
    pixels = []
    for x in range(max(0, math.floor(cx - radius)), min(lattice_x, math.ceil(cx + radius) + 1)):
        for y in range(max(0, math.floor(cy - radius)), min(lattice_y, math.ceil(cy + radius) + 1)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= radius_squared:
                pixels.append((x, y))
    if not pixels:
        raise ValueError(f"no lattice pixels rasterized for centre {centre}")
    return pixels


def initial_cell_pixels(
    centres: Sequence[Centre], radius: float, lattice_x: int, lattice_y: int
) -> list[list[Pixel]]:
    """Rasterize all cells and reject overlapping or out-of-bounds layouts."""
    occupied: set[Pixel] = set()
    cells = []
    for centre in centres:
        pixels = disk_pixels(centre, radius, lattice_x, lattice_y)
        overlap = occupied.intersection(pixels)
        if overlap:
            raise ValueError(f"initial seed cells overlap at {min(overlap)}")
        occupied.update(pixels)
        cells.append(pixels)
    return cells


def packed_cluster_pixels(
    centres: Sequence[Centre], coverage_radius: float, lattice_x: int, lattice_y: int
) -> list[list[Pixel]]:
    """Create a contiguous, Voronoi-like aggregate around hex-packed centres.

    Overlapping coverage disks remove internal Medium channels. Each covered
    pixel belongs to its nearest centre, so cells never overlap and their
    centres retain the requested regular hexagonal arrangement.
    """
    if coverage_radius <= 0:
        raise ValueError("coverage_radius must be positive")
    radius_squared = coverage_radius * coverage_radius
    owners: dict[Pixel, tuple[float, int]] = {}
    for index, (cx, cy) in enumerate(centres):
        for x in range(
            max(0, math.floor(cx - coverage_radius)),
            min(lattice_x, math.ceil(cx + coverage_radius) + 1),
        ):
            for y in range(
                max(0, math.floor(cy - coverage_radius)),
                min(lattice_y, math.ceil(cy + coverage_radius) + 1),
            ):
                distance_squared = (x - cx) ** 2 + (y - cy) ** 2
                if distance_squared > radius_squared:
                    continue
                previous = owners.get((x, y))
                candidate = (distance_squared, index)
                if previous is None or candidate < previous:
                    owners[(x, y)] = candidate

    cells: list[list[Pixel]] = [[] for _ in centres]
    for pixel, (_, index) in owners.items():
        cells[index].append(pixel)
    if any(not pixels for pixels in cells):
        raise ValueError("at least one packed seed cell has no pixels")
    return cells


def assign_types(centres: Sequence[Centre], pattern: str, seed: int) -> list[str]:
    """Assign exactly half A and half B using one of the specified patterns."""
    count = len(centres)
    if count % 2:
        raise ValueError("an exact 50:50 assignment requires an even cell count")

    if pattern == "random":
        types = ["A"] * (count // 2) + ["B"] * (count // 2)
        random.Random(seed).shuffle(types)
        return types

    if pattern == "block":
        # Larger y is defined as the upper half.  The stable index tie-breaker
        # makes the rule exact even if a custom grid has a median y tie.
        upper_indices = {
            index
            for index, _ in sorted(
                enumerate(centres), key=lambda item: (item[1][1], item[0]), reverse=True
            )[: count // 2]
        }
        return ["A" if index in upper_indices else "B" for index in range(count)]

    raise ValueError(f"unknown pattern {pattern!r}")


def minimum_centre_distance(centres: Iterable[Centre]) -> float:
    points = list(centres)
    return min(
        math.dist(points[left], points[right])
        for left in range(len(points))
        for right in range(left + 1, len(points))
    )
