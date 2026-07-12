import sys
from collections import Counter
from pathlib import Path
import unittest


SIMULATION_DIR = Path(__file__).resolve().parents[1] / "Simulation"
sys.path.insert(0, str(SIMULATION_DIR))

from config import PROFILES, REGIMES, load_config  # noqa: E402
from geometry import (  # noqa: E402
    assign_types,
    hexagonal_centres,
    initial_cell_pixels,
    minimum_centre_distance,
    packed_cluster_pixels,
)


class ConfigurationTests(unittest.TestCase):
    def test_profiles_have_required_cell_counts_and_101_export_times(self):
        for name, count in (("development", 100), ("production", 400)):
            config = load_config({"OPENVT_PROFILE": name})
            self.assertEqual(config.profile.cell_count, count)
            self.assertEqual(len(config.export_times), 101)
            self.assertEqual(config.export_times[0], 0)
            self.assertEqual(config.export_times[-1], config.profile.final_mcs)

    def test_all_three_regimes_exist_and_engulfment_roles_are_explicit(self):
        self.assertEqual(set(REGIMES), {"two_clumps", "mixing", "engulfment"})
        self.assertEqual(REGIMES["engulfment"].core_type, "A")
        self.assertEqual(REGIMES["engulfment"].shell_type, "B")

    def test_two_clumps_demixes_within_a_compact_common_aggregate(self):
        regime = REGIMES["two_clumps"]
        gamma_ab = regime.j_ab - (regime.j_aa + regime.j_bb) / 2
        self.assertGreater(gamma_ab, 0)
        self.assertLess(regime.j_ab, regime.j_a_medium + regime.j_b_medium)

    def test_engulfment_demixes_and_preserves_complete_b_wetting(self):
        regime = REGIMES["engulfment"]
        gamma_ab = regime.j_ab - (regime.j_aa + regime.j_bb) / 2
        gamma_a_medium = regime.j_a_medium - regime.j_aa / 2
        gamma_b_medium = regime.j_b_medium - regime.j_bb / 2
        self.assertGreater(gamma_ab, 0)
        self.assertGreater(gamma_a_medium, gamma_ab + gamma_b_medium)

    def test_temperature_can_be_overridden_for_benchmarking(self):
        config = load_config({"OPENVT_TEMPERATURE": "20"})
        self.assertEqual(config.fluctuation_a, 20.0)
        self.assertEqual(config.fluctuation_b, 20.0)

    def test_regimes_select_the_benchmarked_default_temperature(self):
        sorting = load_config({"OPENVT_REGIME": "two_clumps"})
        mixing = load_config({"OPENVT_REGIME": "mixing"})
        engulfment = load_config({"OPENVT_REGIME": "engulfment"})
        self.assertEqual((sorting.fluctuation_a, sorting.fluctuation_b), (10.0, 10.0))
        self.assertEqual((mixing.fluctuation_a, mixing.fluctuation_b), (10.0, 10.0))
        self.assertEqual((engulfment.fluctuation_a, engulfment.fluctuation_b), (13.0, 7.8))

    def test_type_specific_fluctuation_override(self):
        config = load_config(
            {
                "OPENVT_REGIME": "engulfment",
                "OPENVT_FLUCTUATION_A": "12.5",
                "OPENVT_FLUCTUATION_B": "8.25",
            }
        )
        self.assertEqual((config.fluctuation_a, config.fluctuation_b), (12.5, 8.25))

    def test_invalid_final_mcs_is_rejected(self):
        with self.assertRaises(ValueError):
            load_config({"OPENVT_FINAL_MCS": "101"})


class InitializationTests(unittest.TestCase):
    def _centres(self, profile_name):
        profile = PROFILES[profile_name]
        return hexagonal_centres(
            profile.rows,
            profile.columns,
            6.0,
            profile.lattice_x,
            profile.lattice_y,
        )

    def test_both_profiles_form_non_overlapping_hexagonal_seed_grids(self):
        for name in PROFILES:
            profile = PROFILES[name]
            centres = self._centres(name)
            self.assertEqual(len(centres), profile.cell_count)
            self.assertAlmostEqual(minimum_centre_distance(centres), 6.0)
            cells = initial_cell_pixels(
                centres, 2.8, profile.lattice_x, profile.lattice_y
            )
            self.assertEqual(len(cells), profile.cell_count)
            flat = [pixel for cell in cells for pixel in cell]
            self.assertEqual(len(flat), len(set(flat)))

    def test_packed_initializer_has_target_sized_cells_and_no_medium_channels(self):
        profile = PROFILES["development"]
        centres = hexagonal_centres(
            profile.rows, profile.columns, 5.4, profile.lattice_x, profile.lattice_y
        )
        cells = packed_cluster_pixels(centres, 3.2, profile.lattice_x, profile.lattice_y)
        areas = [len(cell) for cell in cells]
        self.assertGreaterEqual(min(areas), 20)
        self.assertLessEqual(max(areas), 33)

        occupied = {pixel for cell in cells for pixel in cell}
        pending = [next(iter(occupied))]
        visited = {pending[0]}
        while pending:
            x, y = pending.pop()
            for neighbour in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if neighbour in occupied and neighbour not in visited:
                    visited.add(neighbour)
                    pending.append(neighbour)
        self.assertEqual(visited, occupied)

    def test_seeded_random_is_reproducible_and_exactly_balanced(self):
        centres = self._centres("production")
        first = assign_types(centres, "random", 17)
        self.assertEqual(first, assign_types(centres, "random", 17))
        self.assertNotEqual(first, assign_types(centres, "random", 18))
        self.assertEqual(Counter(first), {"A": 200, "B": 200})

    def test_block_has_upper_half_a_and_lower_half_b(self):
        centres = self._centres("development")
        types = assign_types(centres, "block", 999)
        a_y = [y for (_, y), cell_type in zip(centres, types) if cell_type == "A"]
        b_y = [y for (_, y), cell_type in zip(centres, types) if cell_type == "B"]
        self.assertEqual(Counter(types), {"A": 50, "B": 50})
        self.assertGreater(min(a_y), max(b_y))


if __name__ == "__main__":
    unittest.main()
