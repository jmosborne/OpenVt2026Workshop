#!/usr/bin/env bash
set -euo pipefail

CALIBRATION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "${CALIBRATION_DIR}/../.." && pwd)"
CC3D_RUNNER="${CC3D_RUNNER:-${WORKSPACE_DIR}/CompuCell3D/runScript.command}"

if [[ ! -x "${CC3D_RUNNER}" ]]; then
    echo "Set CC3D_RUNNER to the executable CompuCell3D runScript.command path." >&2
    exit 2
fi

exec "${CC3D_RUNNER}" -i "${CALIBRATION_DIR}/MotilityCalibration.cc3d" "$@"
