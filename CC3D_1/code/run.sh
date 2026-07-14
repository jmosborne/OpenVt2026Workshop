#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "${CC3D_RUNNER:-}" ]]; then
    for candidate in \
        "${PROJECT_DIR}/../../CompuCell3D/runScript.command" \
        "${PROJECT_DIR}/../../../CompuCell3D/runScript.command"; do
        if [[ -x "${candidate}" ]]; then
            CC3D_RUNNER="${candidate}"
            break
        fi
    done
fi

if [[ -z "${CC3D_RUNNER:-}" || ! -x "${CC3D_RUNNER}" ]]; then
    echo "Set CC3D_RUNNER to the executable CompuCell3D runScript.command path." >&2
    exit 2
fi

: "${OPENVT_PROFILE:=development}"
: "${OPENVT_REGIME:=two_clumps}"
: "${OPENVT_PATTERN:=random}"
: "${OPENVT_SEED:=1}"
export OPENVT_PROFILE OPENVT_REGIME OPENVT_PATTERN OPENVT_SEED

exec "${CC3D_RUNNER}" -i "${PROJECT_DIR}/CellSorting.cc3d" "$@"
