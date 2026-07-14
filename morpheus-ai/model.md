# Morpheus cell-sorting model

This folder contains the Morpheus implementation of the OpenVT 2026 cell-sorting reference model.

The model is a two-dimensional Cellular Potts Model on a hexagonal lattice. It contains two biological cell types and medium, with area regulation, connectivity, stochastic Metropolis motion, and differential contact energies. It has no surface constraint, directed motion, signaling, chemotaxis, division, or death.

## Files

- `code/sorting.xml`: self-contained sorting scenario.
- `code/checkerboard.xml`: self-contained checkerboard scenario.
- `code/engulfment.xml`: self-contained engulfment scenario.
- `code/motility_calibration.xml`: isolated-cell motility calibration.
- `code/export_portal_csv.py`: converter and validator for the OpenVT portal schema.
- `code/morpheusml_calibrated_passive.xml`: exact model for the additional calibrated passive pilot.
- `code/generate_model_calibrated_passive.py`: parameterized generator for that pilot family.
- `code/export_portal_csv_calibrated.py` and `code/validate_portal_csv_calibrated.py`: standalone
  converter and validator supporting calibrated non-integer model times.
- `data/`: portal-ready development CSV files and their provenance records.

## Parameters

Each scenario XML defaults to its 100-cell development case. Contact energies use the Morpheus convention: smaller contact energy means stronger adhesion.

| Regime | init_mode | J_AA lattice | J_BB lattice | J_AB lattice | J_Am lattice | J_Bm lattice |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Sorting | 0 | 0.0 | 0.0 | 3.0 | 2.0 | 2.0 |
| Checkerboard | 1 | 1.5 | 1.5 | 0.0 | 1.1 | 1.1 |
| Engulfment | 1 | 0.0 | -0.5 | 0.0 | 1.1 | 1.5 |

`init_mode=0` gives an exactly balanced deterministic shuffled state. `init_mode=1` gives an exactly balanced upper/lower block state. The same temperature, MCS duration, and area-constraint strength are used for all regimes.

Type conversion is restricted to `time < 0.5`; this prevents cells in block-initialized scenarios from changing type later when they cross the original midline.

The shared Metropolis temperature is `1` and `MCSDuration` is `1`. Sorting uses `J_Am=J_Bm=2`, matching the isolated-cell calibration value `J_cm=2`.

The real target cell area is fixed at `target_area_real=1`. `dx` is the real length represented by one lattice spacing, and Morpheus receives the derived lattice target

```text
target_area_lattice = target_area_real / dx^2
area_strength_lattice = area_strength_real * dx^4
```

The real area stiffness defaults to `area_strength_real=43.2`, which gives the calibrated Morpheus lattice strength `0.3` at `dx=1/sqrt(12)`.

Contact energies represent line energies and are converted as

```text
J_lattice = J_real * dx
```

The real defaults are chosen so the tabled lattice values are recovered at `dx=1/sqrt(12)`.

The calibrated default is `dx=1/sqrt(12)`, corresponding to 12 target lattice sites per cell. At this resolution, a 20-seed isolated-cell ensemble with `J_cm=2` produced MSD `0.996 CD^2` at time 100, 0.37% below target and within the requested 10% tolerance. Mean final area was `0.671 CD^2`, 14.6% below the geometric target `pi/4 = 0.785 CD^2`.

Initialization uses `packing_factor=0.8`, multiplying the analytical lattice-space cell diameter, because diameter spacing left discrete medium gaps at this coarse resolution. Sorting keeps `J_AB=3.0` below the two-interface wetting threshold `2*J_cm=4.0`, preventing medium from splitting the A/B interface. With homotypic energies `J_AA=J_BB=0`, its 100-cell run reaches two compact clumps; the accepted 400-cell run remains cohesive and reaches stable, strongly segregated domains without detached cells.

The optional checkerboard run ends as a compact interspersed aggregate. In the optimized engulfment model, favorable B-B contacts form a dense green inner ball while the higher B-medium energy favors a compact purple outer ring without dispersing cells.

The final 400-cell production endpoints were selected from the heterotypic cell-cell boundary length, expressed in target-cell diameters. The endpoint is accepted when consecutive final windows are within approximately 5%; individual samples remain noisy because the interface fluctuates thermally.

| Scenario | StopTime | Logger interval | Previous-window mean | Final-window mean | Change |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sorting | 80000 | 800 | 22.54 | 22.40 | -0.64% |
| Checkerboard | 25000 | 250 | 394.37 | 393.21 | -0.30% |
| Engulfment | 80000 | 800 | 149.75 | 157.40 | +5.10% |

The portal-ready production files are `data/sorting_400.csv`, `data/checkerboard_400.csv`, and `data/engulfment_400.csv`.

`data/sorting_100_seed10.csv` has been rescaled to the area-derived diameter, but its trajectory predates removal of directed motion and is retained only as a legacy result. It is not validation output for the current mechanics.

## Coordinate scaling and portal export

Coordinates and other spatial observables are converted from lattice to real units and then divided by the diameter of a circle with real target area `A`:

```text
d_cell = 2 * sqrt(A / pi)
x_CD = x_lattice * dx / d_cell
```

Convert a completed Morpheus logger file with:

```powershell
python code/export_portal_csv.py runs/sorting-400-jm2-jab3-80000-seed-0/portal_raw.csv data/sorting_400.csv --expected-cells 400 --target-area 1 --dx 0.288675134594813
```

The exporter requires exactly 101 evenly spaced integer times, stable cell IDs, exactly two integer cell types, and finite coordinates. It writes the exact portal columns `simID,time,cellID,cellType,x,y`, with `simID=0`.

## Model execution

Morpheus accepts contact energies, initialization mode, random seed, grid size, temperature, real target area, spatial resolution `dx`, and area-constraint strength through `--set`. Structural time and logger intervals are explicit XML values because Morpheus resolves them before global symbols.

The committed production configurations use scenario-specific stop times and logger intervals from the table above. Every logger interval is `StopTime/100`, giving 101 data points; plot intervals are `StopTime/10`, giving 11 image frames. Use seed 0 for final production output. Development robustness checks use seeds 0, 1, and 2.

Before increasing `grid_n` from 10 to 20, validate all three regimes with 100 cells. For a 400-cell run that has not plateaued, extend only the stop time and keep all physical parameters unchanged.

## Additional calibrated passive development pilot

`data/sorting_100_seed20260712_calibrated_passive.csv` is an independent 100-cell
development result generated with Morpheus 2.4.1. It is included for portal comparison and is
not a replacement for the active-motility result above.

The pilot uses a square-lattice CPM with target area 200, area-constraint strength 1,
`T=3`, `J_AA=J_BB=8`, `J_AB=16`, and `J_Am=J_Bm=16`. There is no active
`DirectedMotion` term. An isolated-cell MSD measurement gave the preliminary clock conversion
`MCSDuration=0.011763426983168733`; 25,000 MCS therefore correspond to 294.086 model-time
units.

The submitted CSV has `simID=0`, the exact portal header, 10,100 rows, 101 evenly spaced
times, 100 stable cell IDs per time, and 50 cells of each type at every time. Its accompanying
manifest records the exact model SHA-256, parameters, seed, duration, and software version.

This run shows substantial but incomplete segregation. A local six-nearest-centre-neighbour
proxy falls from 0.473 to 0.254, but the final proxy graph still contains four A components and
two B components. The workshop portal's Delaunay/Voronoi contact-length calculation remains
authoritative, and this file should be treated as a development pilot rather than an equilibrated
production result.

Coordinates in this CSV use the equivalent-circle diameter
`sqrt(4*target_area/pi)`. The preliminary MSD clock used ideal hexagonal packed spacing; repeat
the calibration with a measured relaxed or packed-state diameter before using this run for final
cross-framework kinetic comparisons.

Validate the submitted file from the `morpheus-ai` directory with:

```sh
python3 code/validate_portal_csv_calibrated.py \
  data/sorting_100_seed20260712_calibrated_passive.csv --cells 100
```

The complete parameter screens, calibration summaries, visualizations, and batch tooling are in
the [companion Morpheus repository](https://github.com/systems-mechanobiology/morpheus_trials/tree/agent/accelerated-sorting).
