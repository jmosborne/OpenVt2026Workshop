# OpenVT 2026 Cell Sorting

This is a 2D CompuCell3D Cellular Potts Model of two non-growing biological
cell types, A and B. Sorting is produced only by volume exclusion, stochastic
Potts copy attempts, and differential contact energies. There is no signalling,
chemotaxis, persistent-force term, proliferation, apoptosis, or growth.

## Model definition

The lattice has `z=1` and no-flux boundaries. Unoccupied sites are Medium, so
the initialized cluster is surrounded by an explicit Medium type. Every cell
has target area 25 and volume-constraint coefficient 2. Potts fluctuation
amplitude (temperature) is the only motility/noise parameter. Cell centres start on a triangular lattice
(regular hexagonal packing) with spacing 5.4. Nearest-centre assignment creates
a contiguous, Voronoi-like aggregate at approximately target volume, with
Medium around the aggregate rather than threaded through it.

Contact energies use one convention throughout: **lower J means a more
favourable interface**. The three supplied regimes are:

| regime | T(A) | T(B) | J(A,A) | J(B,B) | J(A,B) | J(A,Medium) | J(B,Medium) | expected state |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `two_clumps` | 10 | 10 | 8 | 8 | 24 | 18 | 18 | two compact homotypic domains |
| `mixing` | 10 | 10 | 16 | 16 | 4 | 18 | 18 | heterotypic mixing/checkerboard |
| `engulfment` | 13 | 7.8 | 8 | 12 | 16 | 24 | 14 | segregated A core, B shell |

For two-clump sorting, the effective A-B tension is 16, driving complete type
segregation. `J(A,B)=24` remains below the two-Medium-interface cost of 36,
keeping the domains in a common compact aggregate while they coarsen.
For engulfment, the effective tensions are 6 for A-B, 20 for A-Medium, and 8
for B-Medium. Thus A-B demixing is favourable while
`20 > 6 + 8` preserves complete wetting by the explicit B shell type.

## Run profiles and patterns

| profile | grid | cells | lattice | final MCS | export interval |
|---|---:|---:|---:|---:|---:|
| `development` | 10×10 | 100 | 96×96×1 | 50,000 | 500 |
| `production` | 20×20 | 400 | 160×160×1 | 100,000 | 1,000 |

Both `random` and `block` always contain exactly 50% A and 50% B. `random`
shuffles an exact half-A/half-B list with `OPENVT_SEED`; it does not sample
types independently. `block` assigns A to the upper half (larger y) and B to
the lower half.

From this directory, the default development run is:

```bash
./run.sh
```

Select a production experiment through environment variables:

```bash
OPENVT_PROFILE=production \
OPENVT_REGIME=engulfment \
OPENVT_PATTERN=random \
OPENVT_SEED=42 \
./run.sh -o /absolute/path/to/output
```

Supported variables are `OPENVT_PROFILE` (`development`, `production`),
`OPENVT_REGIME` (`two_clumps`, `mixing`, `engulfment`), `OPENVT_PATTERN`
(`random`, `block`), `OPENVT_SEED`, `OPENVT_TEMPERATURE`,
`OPENVT_FLUCTUATION_A`, `OPENVT_FLUCTUATION_B`, `OPENVT_SIM_ID`, and
`OPENVT_OUTPUT_DIR`. `OPENVT_FINAL_MCS` is a testing override and must be a
positive multiple of 100; normal experiments should use the profile default.
If the runner is elsewhere, set `CC3D_RUNNER` to its `runScript.command`.

## Output contract

`cell_positions.csv` has exactly this header:

```text
simID,time,cellID,cellType,x,y
```

It contains one row per biological cell at exactly 101 equally spaced times:
MCS 0, 99 interior times, and final MCS. Medium is the background spin and has
no biological cell ID, so it is not emitted. The exporter checks the cell count
and complete time schedule before closing the file.

Run the pure-Python configuration and initialization tests with:

```bash
python -m unittest discover -s tests -v
```

## Visualizing completed runs

The plotting utility compares three completed CSV exports and writes an
initial/final cell-centre figure plus quantitative time courses:

```bash
python visualize_results.py \
  --two-clumps /path/to/two_clumps/cell_positions.csv \
  --mixing /path/to/mixing/cell_positions.csv \
  --engulfment /path/to/engulfment/cell_positions.csv \
  --output-dir Visualizations
```

The sorting and mixing curves use the type composition of each cell's six
nearest neighbours. The engulfment curves show each type's mean radial
distance from the whole-cluster centre. Snapshot marker size is illustrative;
the CSV contains centres of mass rather than pixel-resolved cell outlines.
