"""Load and parameterize the isolated-cell calibration XML."""

from pathlib import Path

from cc3d import CompuCellSetup
from cc3d.core.XMLUtils import CC3DXMLListPy, Xml2Obj, dictionaryToMapStrStr

from calibration_config import CalibrationConfig


def _plugin(root, name: str):
    return root.getFirstElement("Plugin", dictionaryToMapStrStr({"Name": name}))


def _set_value(parent, name: str, value) -> None:
    parent.getFirstElement(name).updateElementValue(str(value))


def configure_xml(config: CalibrationConfig, simulation_dir: Path) -> None:
    parsed = Xml2Obj()
    root_element = parsed.Parse(str(simulation_dir / "MotilityCalibration.xml"))

    class ParsedXMLTree:
        CC3DXMLElement = root_element

    CompuCellSetup.set_simulation_xml_description(ParsedXMLTree())
    CompuCellSetup.persistent_globals.persistent_holder["calibration_xml_parser"] = parsed
    root = CompuCellSetup.persistent_globals.cc3d_xml_2_obj_converter.root

    potts = root.getFirstElement("Potts")
    potts.getFirstElement("Dimensions").updateElementAttributes(
        dictionaryToMapStrStr(
            {"x": config.lattice_size, "y": config.lattice_size, "z": 1}
        )
    )
    _set_value(potts, "Steps", config.total_steps)
    amplitude = potts.getFirstElement("FluctuationAmplitude")
    amplitude.getFirstElement("FluctuationAmplitudeParameters").updateElementAttributes(
        dictionaryToMapStrStr(
            {"CellType": "Cell", "FluctuationAmplitude": config.temperature}
        )
    )
    _set_value(potts, "RandomSeed", config.seed)

    volume = _plugin(root, "Volume")
    _set_value(volume, "TargetVolume", config.target_volume)
    _set_value(volume, "LambdaVolume", config.lambda_volume)

    contact = _plugin(root, "Contact")
    for element in CC3DXMLListPy(contact.getElements("Energy")):
        pair = frozenset((element.getAttribute("Type1"), element.getAttribute("Type2")))
        if pair == frozenset(("Cell", "Medium")):
            element.updateElementValue(str(config.j_medium))
