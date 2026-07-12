"""Initialization and position export steppables; no biological rules live here."""

from __future__ import annotations

import csv
from pathlib import Path

from cc3d.core.PySteppables import SteppableBasePy

from config import ModelConfig
from geometry import assign_types, hexagonal_centres, packed_cluster_pixels


class HexagonalInitializerSteppable(SteppableBasePy):
    """Create one compact cluster with centres in regular hexagonal packing."""

    def __init__(self, config: ModelConfig):
        super().__init__(frequency=1)
        self.config = config

    def start(self):
        profile = self.config.profile
        centres = hexagonal_centres(
            rows=profile.rows,
            columns=profile.columns,
            spacing=self.config.centre_spacing,
            lattice_x=profile.lattice_x,
            lattice_y=profile.lattice_y,
        )
        cell_pixels = packed_cluster_pixels(
            centres=centres,
            coverage_radius=self.config.initial_radius,
            lattice_x=profile.lattice_x,
            lattice_y=profile.lattice_y,
        )
        type_names = assign_types(centres, self.config.pattern, self.config.seed)

        type_ids = {"A": self.A, "B": self.B}
        for type_name, pixels in zip(type_names, cell_pixels):
            cell = self.new_cell(type_ids[type_name])
            for x, y in pixels:
                self.cell_field[x, y, 0] = cell

        cells = list(self.cell_list)
        counts = {
            "A": sum(cell.type == self.A for cell in cells),
            "B": sum(cell.type == self.B for cell in cells),
        }
        expected = profile.cell_count // 2
        if len(cells) != profile.cell_count or counts != {"A": expected, "B": expected}:
            raise RuntimeError(
                f"initializer invariant failed: cells={len(cells)}, type counts={counts}"
            )


class PositionCSVSteppable(SteppableBasePy):
    """Write exactly 101 snapshots of biological-cell centres of mass."""

    HEADER = ("simID", "time", "cellID", "cellType", "x", "y")

    def __init__(self, config: ModelConfig):
        super().__init__(frequency=1)
        self.config = config
        self._file = None
        self._writer = None
        self._written_times: set[int] = set()

    def start(self):
        if self.config.output_dir is not None:
            output_directory = self.config.output_dir
        elif self.output_dir:
            output_directory = Path(self.output_dir)
        else:
            output_directory = Path(__file__).resolve().parents[1] / "Output" / self.config.sim_id
        output_directory.mkdir(parents=True, exist_ok=True)

        output_path = output_directory / "cell_positions.csv"
        self._file = output_path.open("w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file, lineterminator="\n")
        self._writer.writerow(self.HEADER)
        self._write_snapshot(0)

    def step(self, mcs):
        if mcs in self.config.export_times and mcs not in self._written_times:
            self._write_snapshot(mcs)

    def finish(self):
        final_mcs = self.config.profile.final_mcs
        if final_mcs not in self._written_times:
            self._write_snapshot(final_mcs)
        self._close_and_validate()

    def on_stop(self):
        if self._file is not None:
            self._file.close()

    def _write_snapshot(self, mcs: int) -> None:
        cells = sorted(self.cell_list, key=lambda cell: cell.id)
        if len(cells) != self.config.profile.cell_count:
            raise RuntimeError(
                f"expected {self.config.profile.cell_count} cells at MCS {mcs}, got {len(cells)}"
            )
        names = {self.A: "A", self.B: "B"}
        for cell in cells:
            self._writer.writerow(
                (
                    self.config.sim_id,
                    mcs,
                    cell.id,
                    names[cell.type],
                    f"{cell.xCOM:.8f}",
                    f"{cell.yCOM:.8f}",
                )
            )
        self._file.flush()
        self._written_times.add(mcs)

    def _close_and_validate(self) -> None:
        expected = set(self.config.export_times)
        if self._written_times != expected:
            missing = sorted(expected - self._written_times)
            extra = sorted(self._written_times - expected)
            raise RuntimeError(f"invalid export schedule; missing={missing}, extra={extra}")
        if len(self._written_times) != 101:
            raise RuntimeError(f"expected 101 export times, got {len(self._written_times)}")
        self._file.close()
        self._file = None
