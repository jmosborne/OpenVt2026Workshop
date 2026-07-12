# Morpheus cell-sorting model

This folder contains the Morpheus implementation of the OpenVT 2026 cell-sorting reference model.

The model is a two-dimensional Cellular Potts Model on a hexagonal lattice. It contains two biological cell types and medium, with volume regulation, connectivity, stochastic Metropolis motion, an uncorrelated random `DirectedMotion` direction redrawn every MCS, and differential contact energies. It has no surface constraint, signaling, chemotaxis, division, or death.

## Files

- `code/morpheusml.xml`: 100- or 400-cell sorting, checkerboard, and engulfment model.
- `code/motility_calibration.xml`: isolated-cell motility calibration.
- `code/export_portal_csv.py`: converter and validator for the OpenVT portal schema.
- `data/`: final portal-ready 400-cell CSV files.

## Parameters

The default XML is the 100-cell sorting development case. Contact energies use the Morpheus convention: smaller contact energy means stronger adhesion.

| Regime | init_mode | J_AA | J_BB | J_AB | J_Am | J_Bm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Sorting | 0 | 0.2 | 0.2 | 5.0 | 6.0 | 6.0 |
| Checkerboard/mixing | 1 | 1.0 | 1.0 | 0.6 | 1.2 | 1.2 |
| Engulfment | 1 | 1.4 | 0.2 | 1.1 | 1.6 | 1.6 |

`init_mode=0` gives an exactly balanced deterministic shuffled state. `init_mode=1` gives an exactly balanced upper/lower block state. The same temperature, MCS duration, and calibrated directed-motion strength are used for all regimes.

The shared Metropolis temperature is `1`, `DirectedMotion` strength is `0.2`, and `MCSDuration` is `0.72`. Each cell draws a new angle uniformly from `[0, 2*pi)` every MCS and updates its unit `move_dir` vector. A 20-seed isolated-cell calibration produced mean MSD `0.981 CD^2` at time 100, 1.9% below the target.

The final 100-cell sorting run used seed 10. It showed broad sorted domains by time 7500 and completed time 25000 in 9 minutes 3 seconds. Its portal-ready output is `data/sorting_100_seed10.csv`.

## Coordinate scaling and portal export

Coordinates are divided by the predicted diameter of a spherical cell with target volume `V`:

```text
d_cell = 2 * (3 * V / (4 * pi))^(1/3)
```

Convert a completed Morpheus logger file with:

```powershell
python code/export_portal_csv.py runs/sorting-400/portal_raw.csv data/sorting_400.csv --expected-cells 400 --target-volume 200
```

The exporter requires exactly 101 evenly spaced integer times, stable cell IDs, exactly two integer cell types, and finite coordinates. It writes the exact portal columns `simID,time,cellID,cellType,x,y`, with `simID=0`.

## Model execution

Morpheus accepts contact energies, initialization mode, random seed, grid size, temperature, target volume, and directed-motion strength through `--set`. Structural time and logger intervals are explicit XML values because Morpheus resolves them before global symbols.

The committed production configuration uses `StopTime=25000`, logger interval `250`, and plot interval `2500`, giving 101 data points and 11 image frames. Use seed 0 for final production output. Development robustness checks use seeds 0, 1, and 2.

Before increasing `grid_n` from 10 to 20, validate all three regimes with 100 cells. For a 400-cell run that has not plateaued, extend only the stop time and keep all physical parameters unchanged.
