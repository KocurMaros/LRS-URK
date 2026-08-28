#!/usr/bin/env bash
# Undo files and configuration created by install_ubuntu_24.sh.
set -Eeuo pipefail

readonly STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/lrs-urk-installer"
readonly STATE_FILE="$STATE_DIR/manifest.env"
readonly BASHRC_FILE="${BASHRC_FILE:-$HOME/.bashrc}"
readonly ENV_START='# >>> LRS-URK installer >>>'
readonly ENV_END='# <<< LRS-URK installer <<<'

PURGE_PACKAGES=0
ASSUME_YES=0

log() { printf '\n[LRS-URK uninstall] %s\n' "$*"; }
die() { printf '\n[LRS-URK uninstall] ERROR: %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Usage: scripts/uninstall_ubuntu_24.sh [options]

By default, remove the installer-managed shell block, cloned repositories,
and build directory only when the install manifest says the installer created
them. Pre-existing source directories are left untouched.

Options:
  --purge-packages  Also remove explicitly requested apt packages that were not
                    installed before the first installer run, plus apt/rosdep
                    source files created by the installer. Shared dependency
                    packages and GeographicLib datasets are retained.
  -y, --yes         Do not ask for confirmation.
  -h, --help        Show this help.
EOF
}

while (($#)); do
  case "$1" in
    --purge-packages) PURGE_PACKAGES=1 ;;
    -y|--yes) ASSUME_YES=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1 (use --help)" ;;
  esac
  shift
done

[[ $EUID -ne 0 ]] || die "Run this script as your normal user, not as root."

remove_environment_block() {
  local output starts ends
  [[ -f "$BASHRC_FILE" ]] || return 0
  starts="$(grep -Fxc "$ENV_START" "$BASHRC_FILE" || true)"
  ends="$(grep -Fxc "$ENV_END" "$BASHRC_FILE" || true)"
  [[ "$starts" == "$ends" ]] || \
    die "The managed markers in $BASHRC_FILE are incomplete; refusing to rewrite it."
  output="$(mktemp "${BASHRC_FILE}.lrs-urk.XXXXXX")"
  awk -v start="$ENV_START" -v end="$ENV_END" '
    $0 == start { skipping = 1; next }
    $0 == end   { skipping = 0; next }
    !skipping   { print }
  ' "$BASHRC_FILE" > "$output"
  chmod --reference="$BASHRC_FILE" "$output"
  mv -f -- "$output" "$BASHRC_FILE"
}

if [[ ! -f "$STATE_FILE" ]]; then
  log "No install manifest found; only removing the managed shell block if present"
  remove_environment_block
  exit 0
fi

NEW_PACKAGES=()
REMOVED_PACKAGES=()
# shellcheck disable=SC1090
source "$STATE_FILE"
[[ "${STATE_VERSION:-}" == 1 ]] || die "Unsupported installer state in $STATE_FILE"

if ((!ASSUME_YES)); then
  printf 'This will remove installer-owned source/build directories and shell configuration.\n'
  ((PURGE_PACKAGES)) && printf 'It will also remove packages recorded as newly installed.\n'
  read -r -p 'Continue? [y/N] ' answer
  [[ "$answer" == y || "$answer" == Y ]] || { log "Cancelled"; exit 0; }
fi

safe_remove_checkout() {
  local path expected="$2" origin
  path="$(realpath -m -- "$1")"
  [[ -e "$path" ]] || return 0
  [[ -d "$path/.git" ]] || die "Refusing to remove $path because it is not a Git checkout."
  origin="$(git -C "$path" remote get-url origin 2>/dev/null || true)"
  case "$origin" in
    *"github.com:ArduPilot/$expected.git"|*"github.com/ArduPilot/$expected.git"|*"github.com/ArduPilot/$expected") ;;
    *) die "Refusing to remove $path because its origin is not ArduPilot/$expected." ;;
  esac
  [[ "$path" != / && "$path" != "$HOME" && "$path" == "$HOME/"* ]] || \
    die "Refusing unsafe removal path: $path"
  log "Removing installer-created checkout $path"
  rm -rf -- "$path"
}

remove_environment_block

if [[ "${CREATED_ARDUPILOT_GAZEBO:-0}" == 1 ]]; then
  safe_remove_checkout "$ARDUPILOT_GAZEBO_DIR" ardupilot_gazebo
elif [[ "${CREATED_GAZEBO_BUILD:-0}" == 1 && -e "$ARDUPILOT_GAZEBO_BUILD_DIR" ]]; then
  [[ "$ARDUPILOT_GAZEBO_BUILD_DIR" == "$ARDUPILOT_GAZEBO_DIR/"* ]] || \
    die "Refusing build directory outside the Gazebo checkout: $ARDUPILOT_GAZEBO_BUILD_DIR"
  log "Removing installer-created plugin build $ARDUPILOT_GAZEBO_BUILD_DIR"
  rm -rf -- "$ARDUPILOT_GAZEBO_BUILD_DIR"
else
  log "Leaving pre-existing ArduPilot Gazebo checkout untouched"
fi

if [[ "${CREATED_ARDUPILOT:-0}" == 1 ]]; then
  safe_remove_checkout "$ARDUPILOT_DIR" ardupilot
else
  log "Leaving pre-existing ArduPilot checkout untouched"
fi

if [[ -d "$STATE_DIR/ardupilot-home" ]]; then
  log "Removing the installer-owned ArduPilot Python environment"
  rm -rf -- "$STATE_DIR/ardupilot-home"
elif [[ "${ARDUPILOT_VENV_DIR:-}" == "$ARDUPILOT_DIR/"* && \
        -f "${ARDUPILOT_VENV_DIR:-}/pyvenv.cfg" ]]; then
  log "Leaving a virtual environment inside the pre-existing ArduPilot checkout untouched"
fi

if ((PURGE_PACKAGES)); then
  log "Removing system configuration created by the installer"
  sudo -v
  if [[ "${CREATED_GAZEBO_ROSDEP_SOURCE:-0}" == 1 ]]; then
    sudo rm -f -- /etc/ros/rosdep/sources.list.d/00-gazebo.list
  fi
  if [[ "${CREATED_DEFAULT_ROSDEP_SOURCE:-0}" == 1 ]]; then
    sudo rm -f -- /etc/ros/rosdep/sources.list.d/20-default.list
  fi
  if ((${#NEW_PACKAGES[@]})); then
    sudo env DEBIAN_FRONTEND=noninteractive apt-get remove -y "${NEW_PACKAGES[@]}"
  fi
  if ((${#REMOVED_PACKAGES[@]})); then
    sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y "${REMOVED_PACKAGES[@]}"
  fi
  if [[ "${ADDED_DIALOUT:-0}" == 1 ]]; then
    sudo gpasswd -d "$USER" dialout >/dev/null || true
  fi
  if [[ "${INSTALLED_ROS_APT_SOURCE:-0}" == 1 ]] && \
      dpkg-query -W ros2-apt-source >/dev/null 2>&1; then
    sudo env DEBIAN_FRONTEND=noninteractive apt-get remove -y ros2-apt-source
  fi
  sudo apt-get update
  rm -f -- "$STATE_FILE"
  rmdir "$STATE_DIR" 2>/dev/null || true
else
  log "System packages remain installed. The manifest is retained so you can later run:"
  printf '  %q --purge-packages --yes\n' "$0"
fi

log "Uninstall complete. Open a new terminal to discard the old environment."
