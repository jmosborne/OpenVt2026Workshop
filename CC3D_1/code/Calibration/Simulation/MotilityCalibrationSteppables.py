"""Initialize and track one freely fluctuating isolated CPM cell."""

from __future__ import annotations

import csv
from pathlib import Path

from cc3d.core.PySteppables import SteppableBasePy

from calibration_config import CalibrationConfig


class IsolatedCellInitializer(SteppableBasePy):
    def __init__(self, config: CalibrationConfig):
        super().__init__(frequency=1)
        self.config = config

    def start(self):
        cell = self.new_cell(self.CELL)
        centre = self.config.lattice_size // 2
        # Exactly target volume; burn-in removes this square-shape transient.
        self.cell_field[centre - 2 : centre + 3, centre - 2 : centre + 3, 0] = cell


class CalibrationTracker(SteppableBasePy):
    HEADER = ("condition", "seed", "mcs", "x", "y", "volume")

    def __init__(self, config: CalibrationConfig):
        super().__init__(frequency=1)
        self.config = config
        self._file = None
        self._writer = None
        self._samples = 0

    def start(self):
        if self.output_dir:
            output_dir = Path(self.output_dir)
        else:
            output_dir = Path(__file__).resolve().parents[1] / "Output" / self.config.condition
        output_dir.mkdir(parents=True, exist_ok=True)
        self._file = (output_dir / "calibration_positions.csv").open(
            "w", newline="", encoding="utf-8"
        )
        self._writer = csv.writer(self._file, lineterminator="\n")
        self._writer.writerow(self.HEADER)

    def step(self, mcs):
        relative_mcs = mcs - self.config.burn_in_mcs
        if relative_mcs < 0 or relative_mcs % self.config.sample_interval_mcs:
            return
        cells = list(self.cell_list)
        if len(cells) != 1:
            raise RuntimeError(f"expected one calibration cell at MCS {mcs}, got {len(cells)}")
        cell = cells[0]
        self._writer.writerow(
            (
                self.config.condition,
                self.config.seed,
                relative_mcs,
                f"{cell.xCOM:.10f}",
                f"{cell.yCOM:.10f}",
                cell.volume,
            )
        )
        self._samples += 1

    def finish(self):
        self._file.close()
        if self._samples != self.config.expected_samples:
            raise RuntimeError(
                f"expected {self.config.expected_samples} samples, got {self._samples}"
            )

    def on_stop(self):
        if self._file is not None:
            self._file.close()
