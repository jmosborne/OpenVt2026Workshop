"""CompuCell3D entry point for the OpenVT 2026 cell-sorting model."""

from cc3d import CompuCellSetup


from config import load_config  # noqa: E402
from CellSortingSteppables import (  # noqa: E402
    HexagonalInitializerSteppable,
    PositionCSVSteppable,
)
import xml_config  # noqa: E402


CONFIG = load_config()
xml_config.configure_xml(CONFIG, xml_config.Path(xml_config.__file__).resolve().parent)

CompuCellSetup.register_steppable(steppable=HexagonalInitializerSteppable(CONFIG))
CompuCellSetup.register_steppable(steppable=PositionCSVSteppable(CONFIG))
CompuCellSetup.run()
