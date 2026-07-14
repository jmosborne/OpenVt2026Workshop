"""Load the readable base XML and apply one validated model configuration."""

from pathlib import Path

from cc3d import CompuCellSetup
from cc3d.core.XMLUtils import CC3DXMLListPy, Xml2Obj, dictionaryToMapStrStr

from config import ModelConfig


def _plugin(root, name: str):
    return root.getFirstElement("Plugin", dictionaryToMapStrStr({"Name": name}))


def _set_value(parent, element_name: str, value) -> None:
    element = parent.getFirstElement(element_name)
    if element is None:
        raise RuntimeError(f"missing required XML element {element_name!r}")
    element.updateElementValue(str(value))


def configure_xml(config: ModelConfig, simulation_dir: Path) -> None:
    """Apply the selected profile/regime before C++ plugins initialize."""
    converter = CompuCellSetup.persistent_globals.cc3d_xml_2_obj_converter
    if converter is None or converter.root is None:
        # The headless project loader executes Python before parsing XML.
        # Player uses the same safe path, so parse the project XML explicitly.
        parsed = Xml2Obj()
        root_element = parsed.Parse(str(simulation_dir / "CellSorting.xml"))

        class ParsedXMLTree:
            CC3DXMLElement = root_element

        CompuCellSetup.set_simulation_xml_description(ParsedXMLTree())
        # Xml2Obj owns Python references for every parsed child. Keep it alive
        # for the whole C++ simulation (otherwise SWIG child pointers dangle).
        CompuCellSetup.persistent_globals.persistent_holder["openvt_xml_parser"] = parsed
        converter = CompuCellSetup.persistent_globals.cc3d_xml_2_obj_converter
    root = converter.root

    potts = root.getFirstElement("Potts")
    dimensions = potts.getFirstElement("Dimensions")
    dimensions.updateElementAttributes(
        dictionaryToMapStrStr(
            {
                "x": str(config.profile.lattice_x),
                "y": str(config.profile.lattice_y),
                "z": "1",
            }
        )
    )
    _set_value(potts, "Steps", config.profile.final_mcs)
    amplitudes = {"A": config.fluctuation_a, "B": config.fluctuation_b}
    amplitude_element = potts.getFirstElement("FluctuationAmplitude")
    for element in CC3DXMLListPy(
        amplitude_element.getElements("FluctuationAmplitudeParameters")
    ):
        cell_type = element.getAttribute("CellType")
        element.updateElementAttributes(
            dictionaryToMapStrStr(
                {
                    "CellType": cell_type,
                    "FluctuationAmplitude": str(amplitudes[cell_type]),
                }
            )
        )
    _set_value(potts, "RandomSeed", config.seed)

    volume = _plugin(root, "Volume")
    _set_value(volume, "TargetVolume", config.target_volume)
    _set_value(volume, "LambdaVolume", config.lambda_volume)

    contact = _plugin(root, "Contact")
    energies = {
        frozenset(("Medium",)): 0.0,
        frozenset(("A",)): config.regime.j_aa,
        frozenset(("B",)): config.regime.j_bb,
        frozenset(("A", "B")): config.regime.j_ab,
        frozenset(("A", "Medium")): config.regime.j_a_medium,
        frozenset(("B", "Medium")): config.regime.j_b_medium,
    }
    for element in CC3DXMLListPy(contact.getElements("Energy")):
        pair = frozenset((element.getAttribute("Type1"), element.getAttribute("Type2")))
        element.updateElementValue(str(energies[pair]))
