"""CompuCell3D entry point for isolated-cell motility calibration."""

from cc3d import CompuCellSetup

from calibration_config import load_config
from MotilityCalibrationSteppables import CalibrationTracker, IsolatedCellInitializer
import calibration_xml


CONFIG = load_config()
calibration_xml.configure_xml(CONFIG, calibration_xml.Path(calibration_xml.__file__).resolve().parent)
CompuCellSetup.register_steppable(steppable=IsolatedCellInitializer(CONFIG))
CompuCellSetup.register_steppable(steppable=CalibrationTracker(CONFIG))
CompuCellSetup.run()
