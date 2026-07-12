import csv
import math
import sys
import tempfile
import unittest
from pathlib import Path


CODE_DIR = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE_DIR))

from export_portal_csv import (  # noqa: E402
    ExportError,
    OUTPUT_COLUMNS,
    build_parser,
    convert,
    predicted_cell_diameter,
)


class ExportPortalCsvTests(unittest.TestCase):
    def test_predicted_diameter_for_unit_radius_sphere(self):
        volume = 4.0 * math.pi / 3.0
        self.assertAlmostEqual(predicted_cell_diameter(volume), 2.0)

    def test_rejects_non_positive_or_non_finite_volume(self):
        for value in (0.0, -1.0, math.inf, math.nan):
            with self.subTest(value=value), self.assertRaises(ExportError):
                predicted_cell_diameter(value)

    def test_target_volume_argument_is_required(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["raw.csv", "out.csv", "--expected-cells", "100"])

    def test_converts_valid_100_cell_logger_output(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "raw.csv"
            output = Path(directory) / "portal.csv"
            with raw.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(("time", "cell.id", "cell.type", "cell.center.x", "cell.center.y"))
                for time in range(0, 1010, 10):
                    for cell_id in range(1, 101):
                        writer.writerow((time, cell_id, cell_id % 2, 2.0 * cell_id, 4.0))

            target_volume = 4.0 * math.pi / 3.0
            convert(raw, output, expected_cells=100, target_volume=target_volume)

            with output.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(list(rows[0]), list(OUTPUT_COLUMNS))
            self.assertEqual(len(rows), 10_100)
            self.assertEqual(rows[0]["simID"], "0")
            self.assertEqual(rows[0]["x"], "1")
            self.assertEqual(rows[0]["y"], "2")
            self.assertEqual({row["cellType"] for row in rows}, {"0", "1"})

    def test_rejects_changed_cell_id_set(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "raw.csv"
            with raw.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(("time", "cell.id", "cell.type", "cell.center.x", "cell.center.y"))
                for time in range(101):
                    for cell_id in range(1, 101):
                        changed_id = 101 if time == 100 and cell_id == 100 else cell_id
                        writer.writerow((time, changed_id, cell_id % 2, cell_id, cell_id))
            with self.assertRaisesRegex(ExportError, "cell ID set changed"):
                convert(raw, Path(directory) / "out.csv", 100, 200.0)


if __name__ == "__main__":
    unittest.main()
