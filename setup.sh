
#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---kitless}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
VENV_DIR="${VENV_DIR:-${ROOT}/.venv}"
ISAACLAB_DIR="${ISAACLAB_DIR:-${ROOT}/external/IsaacLab}"
ISAACLAB_SHA="9989d276ad825221b10f5a60de92762fd63a0faf"

usage() {
  cat <<'USAGE'
Usage: bash setup.sh [--kitless|--full|--assets|--check]

--kitless  Install the local package plus Newton 1.2.0 and clone pinned Isaac Lab.
--full     Run --kitless and install Isaac Sim 6.0.0.0.
--assets   Create asset/output directories and print artifact guidance.
--check    Run environment checks.
USAGE
}

ensure_python() {
  if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "Python 3.12 not found as ${PYTHON_BIN}. Set PYTHON_BIN=/path/to/python3.12." >&2
    exit 1
  fi
}

install_kitless() {
  ensure_python
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
  python -m pip install --upgrade pip
  python -m pip install -e ".[dev]"
  python -m pip install "newton==1.2.0" cmaes optuna pandas pyarrow tqdm
  mkdir -p "${ROOT}/external"
  if [[ ! -d "${ISAACLAB_DIR}/.git" ]]; then
    git clone https://github.com/isaac-sim/IsaacLab.git "${ISAACLAB_DIR}"
  fi
  git -C "${ISAACLAB_DIR}" fetch origin develop
  git -C "${ISAACLAB_DIR}" checkout "${ISAACLAB_SHA}"
}

install_full() {
  install_kitless
  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
  python -m pip install "isaacsim==6.0.0.0"
}

install_assets() {
  mkdir -p "${ROOT}/assets/robots" "${ROOT}/outputs" "${ROOT}/external"
  cat <<'ASSETS'
Asset directories are ready.

Large datasets, SO-101 benchmark outputs, neural weights, and FMUs should stay
outside git. Add manifests under assets/robots/<robot>/ or docs/artifacts.md
when publishing downloadable artifacts.
ASSETS
}

case "${MODE}" in
  --kitless) install_kitless ;;
  --full) install_full ;;
  --assets) install_assets ;;
  --check) python3 "${ROOT}/check_environment.py" ;;
  --help|-h) usage ;;
  *) usage; exit 1 ;;
esac
