#!/usr/bin/env python3
"""Generate a reproducible OpenVT 2026 cell-sorting Morpheus model."""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent


REGIMES = {
    "sorting": {
        "J_AA": 4.0,
        "J_BB": 4.0,
        "J_AB": 16.0,
        "J_A_medium": 10.0,
        "J_B_medium": 10.0,
        "temperature": 2.0,
        "description": "Homotypic contacts are favoured and unlike contacts are costly.",
    },
    "mixing": {
        "J_AA": 10.0,
        "J_BB": 10.0,
        "J_AB": 2.0,
        "J_A_medium": 10.0,
        "J_B_medium": 10.0,
        "temperature": 5.0,
        "description": "Heterotypic contacts are favoured, giving a mixed checkerboard-like mosaic.",
    },
    "engulfment": {
        "J_AA": 4.0,
        "J_BB": 4.0,
        "J_AB": 8.0,
        "J_A_medium": 16.0,
        "J_B_medium": 6.0,
        "temperature": 2.0,
        "description": "Canonical Morpheus hierarchy: type A is the intended core and type B the shell.",
    },
}


@dataclass(frozen=True)
class ModelConfig:
    cells: int
    pattern: str
    regime: str
    seed: int
    duration: int
    mcs_duration: float
    motility_strength: float
    target_area: float
    temperature: float
    J_AA: float
    J_BB: float
    J_AB: float
    J_A_medium: float
    J_B_medium: float

    @property
    def stop_time(self) -> float:
        return self.duration * self.mcs_duration

    @property
    def cell_diameter(self) -> float:
        return math.sqrt(4.0 * self.target_area / math.pi)

    @property
    def seed_side(self) -> float:
        return math.sqrt(self.target_area)

    @property
    def grid_spacing(self) -> float:
        return 1.2 * self.seed_side

    @property
    def margin(self) -> float:
        return 2.4 * self.seed_side


def number(value: float | int) -> str:
    return f"{value:.12g}"


def initial_sites(config: ModelConfig) -> list[tuple[int, str, float, float]]:
    side = math.isqrt(config.cells)
    if side * side != config.cells or side % 2:
        raise ValueError("cells must form an even square grid")

    types = ["A"] * (config.cells // 2) + ["B"] * (config.cells // 2)
    if config.pattern == "random":
        random.Random(config.seed).shuffle(types)
    else:
        # Morpheus y increases upwards: B occupies low-y rows and A high-y rows.
        types = ["B" if row < side // 2 else "A" for row in range(side) for _ in range(side)]

    sites = []
    vertical_spacing = config.grid_spacing * math.sqrt(3.0) / 2.0
    for index, cell_type in enumerate(types, start=1):
        row, column = divmod(index - 1, side)
        center_x = config.margin + column * config.grid_spacing + (row % 2) * config.grid_spacing / 2.0
        center_y = config.margin + row * vertical_spacing
        sites.append(
            (
                index,
                cell_type,
                center_x - config.seed_side / 2.0,
                center_y - config.seed_side / 2.0,
            )
        )
    return sites


def population(config: ModelConfig, cell_id: int, cell_type: str, origin_x: float, origin_y: float) -> str:
    return dedent(
        f"""\
        <Population type=\"{cell_type}\" size=\"1\" name=\"{cell_type}-{cell_id}\">
            <InitCellObjects mode=\"distance\">
                <Arrangement displacements=\"1, 1, 1\" repetitions=\"1, 1, 1\">
                    <Box origin=\"{number(origin_x)}, {number(origin_y)}, 0\" size=\"{number(config.seed_side)}, {number(config.seed_side)}, 0\"/>
                </Arrangement>
            </InitCellObjects>
        </Population>"""
    )


def random_motility(config: ModelConfig) -> str:
    if config.motility_strength == 0:
        return ""
    return dedent(
        f"""\
        <Property symbol=\"motility_angle\" value=\"0\"/>
        <PropertyVector symbol=\"move_dir\" value=\"0, 0, 0\"/>
        <DirectedMotion direction=\"move_dir\" strength=\"motility_strength\"/>
        <Event trigger=\"when-true\" time-step=\"{number(config.mcs_duration)}\" name=\"Unbiased direction resampling\">
            <Condition>1</Condition>
            <Rule symbol-ref=\"motility_angle\"><Expression>rand_uni(0, 2*pi)</Expression></Rule>
            <VectorRule symbol-ref=\"move_dir\"><Expression>cos(motility_angle), sin(motility_angle), 0</Expression></VectorRule>
        </Event>"""
    )


def build_model(config: ModelConfig) -> str:
    sites = initial_sites(config)
    side = math.isqrt(config.cells)
    vertical_spacing = config.grid_spacing * math.sqrt(3.0) / 2.0
    lattice_x = math.ceil(
        2.0 * config.margin + (side - 1) * config.grid_spacing + config.grid_spacing / 2.0 + config.seed_side
    )
    lattice_y = math.ceil(2.0 * config.margin + (side - 1) * vertical_spacing + config.seed_side)
    populations = "\n".join(population(config, *site) for site in sites)
    motility = random_motility(config)
    if motility:
        motility_constant = (
            f'\n                <Constant symbol="motility_strength" name="Unbiased active motility strength" '
            f'value="{number(config.motility_strength)}"/>'
        )
        cell_types = dedent(
            f"""\
            <CellType class="biological" name="A">
                <VolumeConstraint target="target_area" strength="1"/>
            {motility}
            </CellType>
            <CellType class="biological" name="B">
                <VolumeConstraint target="target_area" strength="1"/>
            {motility}
            </CellType>
            <CellType class="medium" name="medium"/>"""
        )
    else:
        # Preserve the exact XML layout used by the submitted passive simulation.
        motility_constant = ""
        cell_types = dedent(
            """\
            <CellType class="biological" name="A"><VolumeConstraint target="target_area" strength="1"/></CellType>
            <CellType class="biological" name="B"><VolumeConstraint target="target_area" strength="1"/></CellType>
            <CellType class="medium" name="medium"/>"""
        )
    cell_types = cell_types.replace("\n", "\n                ")
    regime = REGIMES[config.regime]
    title = f"Cell sorting: {config.cells} cells, {config.pattern} layout, {config.regime} regime"

    return dedent(
        f"""\
        <?xml version=\"1.0\" encoding=\"UTF-8\"?>
        <MorpheusModel version=\"4\">
            <Description>
                <Title>{title}</Title>
                <Details>
        OpenVT 2026 cell-sorting model: volume exclusion, non-persistent stochastic CPM motility,
        and differential contact energies only. No signalling, chemotaxis, proliferation, or death.
        The regular hexagonal centre layout contains exactly {config.cells // 2} cells of each type.
        Pattern: {config.pattern}. Regime: {config.regime}. {regime["description"]}
        CPM steps: {config.duration}. Model time per MCS: {number(config.mcs_duration)}.
                </Details>
            </Description>
            <Global>
                <Constant symbol=\"target_area\" name=\"Target cell area (lattice units squared)\" value=\"{number(config.target_area)}\"/>
                <Constant symbol=\"cell_diameter\" name=\"Relaxed cell diameter (lattice units)\" value=\"{number(config.cell_diameter)}\"/>
                <Constant symbol=\"J_AA\" name=\"A-A contact energy\" value=\"{number(config.J_AA)}\"/>
                <Constant symbol=\"J_BB\" name=\"B-B contact energy\" value=\"{number(config.J_BB)}\"/>
                <Constant symbol=\"J_AB\" name=\"A-B contact energy\" value=\"{number(config.J_AB)}\"/>
                <Constant symbol=\"J_A_medium\" name=\"A-medium contact energy\" value=\"{number(config.J_A_medium)}\"/>
                <Constant symbol=\"J_B_medium\" name=\"B-medium contact energy\" value=\"{number(config.J_B_medium)}\"/>
                <Constant symbol=\"T\" name=\"CPM motility temperature\" value=\"{number(config.temperature)}\"/>{motility_constant}
            </Global>
            <Space>
                <SpaceSymbol symbol=\"space\"/>
                <Lattice class=\"square\">
                    <Size symbol=\"size\" value=\"{lattice_x}, {lattice_y}, 0\"/>
                    <BoundaryConditions>
                        <Condition type=\"constant\" boundary=\"x\"/>
                        <Condition type=\"constant\" boundary=\"-x\"/>
                        <Condition type=\"constant\" boundary=\"y\"/>
                        <Condition type=\"constant\" boundary=\"-y\"/>
                    </BoundaryConditions>
                    <Neighborhood><Order>2</Order></Neighborhood>
                </Lattice>
            </Space>
            <Time>
                <StartTime value=\"0\"/>
                <StopTime value=\"{number(config.stop_time)}\"/>
                <RandomSeed value=\"{config.seed}\"/>
                <TimeSymbol symbol=\"time\"/>
            </Time>
            <CellTypes>
                {cell_types}
            </CellTypes>
            <CPM>
                <Interaction default=\"0\">
                    <Contact type1=\"A\" type2=\"A\" value=\"J_AA\"/>
                    <Contact type1=\"B\" type2=\"B\" value=\"J_BB\"/>
                    <Contact type1=\"A\" type2=\"B\" value=\"J_AB\"/>
                    <Contact type1=\"A\" type2=\"medium\" value=\"J_A_medium\"/>
                    <Contact type1=\"B\" type2=\"medium\" value=\"J_B_medium\"/>
                </Interaction>
                <MonteCarloSampler stepper=\"edgelist\">
                    <MCSDuration value=\"{number(config.mcs_duration)}\"/>
                    <Neighborhood><Order>2</Order></Neighborhood>
                    <MetropolisKinetics temperature=\"T\"/>
                </MonteCarloSampler>
                <ShapeSurface scaling=\"norm\"><Neighborhood><Order>6</Order></Neighborhood></ShapeSurface>
            </CPM>
            <CellPopulations>
        {populations}
            </CellPopulations>
            <Analysis>
                <Logger time-step=\"{number(config.stop_time / 100)}\">
                    <Input>
                        <Symbol symbol-ref=\"time\"/>
                        <Symbol symbol-ref=\"cell.id\"/>
                        <Symbol symbol-ref=\"cell.type\"/>
                        <Symbol symbol-ref=\"cell.center.x\"/>
                        <Symbol symbol-ref=\"cell.center.y\"/>
                    </Input>
                    <Output><TextOutput/></Output>
                </Logger>
            </Analysis>
        </MorpheusModel>
        """
    ).lstrip()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", type=int, choices=(100, 400), required=True)
    parser.add_argument("--pattern", choices=("random", "block"), required=True)
    parser.add_argument("--regime", choices=tuple(REGIMES), required=True)
    parser.add_argument("--seed", type=int, default=20260712)
    parser.add_argument("--duration", type=int, default=10000, help="Number of CPM MCS; must be divisible by 100.")
    parser.add_argument("--mcs-duration", type=float, default=1.0, help="Calibrated model-time duration of one MCS.")
    parser.add_argument("--motility-strength", type=float, default=0.0, help="Unbiased direction strength, re-sampled every MCS.")
    parser.add_argument("--target-area", type=float, default=100.0)
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--J-AA", dest="J_AA", type=float)
    parser.add_argument("--J-BB", dest="J_BB", type=float)
    parser.add_argument("--J-AB", dest="J_AB", type=float)
    parser.add_argument("--J-A-medium", dest="J_A_medium", type=float)
    parser.add_argument("--J-B-medium", dest="J_B_medium", type=float)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.duration <= 0 or args.duration % 100:
        parser.error("--duration must be a positive multiple of 100 to export exactly 101 time points")
    if args.target_area <= 0:
        parser.error("--target-area must be positive")
    if args.mcs_duration <= 0:
        parser.error("--mcs-duration must be positive")
    if args.motility_strength < 0:
        parser.error("--motility-strength cannot be negative")
    return args


def config_from_args(args: argparse.Namespace) -> ModelConfig:
    defaults = REGIMES[args.regime]
    values = {}
    for key in ("temperature", "J_AA", "J_BB", "J_AB", "J_A_medium", "J_B_medium"):
        override = getattr(args, key)
        values[key] = defaults[key] if override is None else override
    if values["temperature"] < 0:
        raise ValueError("temperature cannot be negative")
    return ModelConfig(
        cells=args.cells,
        pattern=args.pattern,
        regime=args.regime,
        seed=args.seed,
        duration=args.duration,
        mcs_duration=args.mcs_duration,
        motility_strength=args.motility_strength,
        target_area=args.target_area,
        **values,
    )


def main() -> None:
    args = parse_arguments()
    config = config_from_args(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_model(config), encoding="utf-8")
    print(f"Wrote {config.cells}-cell {config.regime} model to {args.output}")


if __name__ == "__main__":
    main()
