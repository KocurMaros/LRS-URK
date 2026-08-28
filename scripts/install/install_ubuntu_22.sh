#!/usr/bin/env bash
set -euo pipefail

ARDUPILOT_DIR="${ARDUPILOT_DIR:-$HOME/ardupilot}"
ARDUPILOT_GAZEBO_DIR="${ARDUPILOT_GAZEBO_DIR:-$HOME/ardupilot_gazebo}"
ROS_DISTRO=humble
GZ_VERSION=harmonic
LRS_URK_REMOTE=https://github.com/KocurMaros/LRS-URK.git
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LRS_URK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BASHRC="$HOME/.bashrc"
ENV_START='# >>> LRS-URK >>>'
ENV_END='# <<< LRS-URK <<<'
CHECK_ONLY=0
case "${1:-}" in
  --check) CHECK_ONLY=1 ;;
  -h|--help)
    echo "Usage: scripts/install_ubuntu_22.sh [--check]"
    exit 0
    ;;
  '') ;;
  *) echo "Unknown option: $1" >&2; exit 1 ;;
esac


log() { printf '\n==> %s\n' "$*"; }
fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

[[ $EUID -ne 0 ]] || fail "Run this script as your normal user, not as root."

# shellcheck disable=SC1091
source /etc/os-release
[[ "${ID:-}" == ubuntu && "${VERSION_ID:-}" == 22.04 ]] || \
  fail "This installer requires Ubuntu 22.04."

log "Checking Git"
if ! command -v git >/dev/null 2>&1; then
  sudo apt update
  sudo apt install -y git
fi

if ! GIT_TERMINAL_PROMPT=0 timeout 30 git ls-remote "$LRS_URK_REMOTE" HEAD >/dev/null 2>&1; then
  fail "Git cannot access GitHub. Check your internet connection and GitHub configuration."
fi
if (( CHECK_ONLY )); then
  echo "Ubuntu 22.04, Git, and GitHub access are OK."
  exit 0
fi


git -C "$LRS_URK_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 || \
  fail "$LRS_URK_DIR is not a Git checkout. Clone $LRS_URK_REMOTE first."
if git -C "$LRS_URK_DIR" remote get-url origin >/dev/null 2>&1; then
  git -C "$LRS_URK_DIR" remote set-url origin "$LRS_URK_REMOTE"
else
  git -C "$LRS_URK_DIR" remote add origin "$LRS_URK_REMOTE"
fi

log "Installing Ubuntu and ROS 2 prerequisites"
sudo apt update
sudo apt install -y locales software-properties-common curl ca-certificates git-lfs lsb-release gnupg \
  build-essential cmake pkg-config wget
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
sudo add-apt-repository -y universe

log "Adding the Gazebo Harmonic repository"
sudo curl -fsSL https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" |
  sudo tee /etc/apt/sources.list.d/gazebo-stable.list >/dev/null

if ! dpkg-query -W ros2-apt-source >/dev/null 2>&1; then
  ROS_APT_SOURCE_VERSION="$(
    curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest |
      sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' |
      head -n 1
  )"
  [[ -n "$ROS_APT_SOURCE_VERSION" ]] || fail "Could not find the ROS apt source release."
  ROS_APT_DEB="/tmp/ros2-apt-source.deb"
  curl -fL -o "$ROS_APT_DEB" \
    "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.${UBUNTU_CODENAME:-${VERSION_CODENAME}}_all.deb"
  sudo dpkg -i "$ROS_APT_DEB"
  rm -f "$ROS_APT_DEB"
fi

sudo apt update
sudo apt install -y ros-humble-desktop ros-dev-tools gz-harmonic ros-humble-ros-gzharmonic \
  ros-humble-mavros libgz-sim8-dev rapidjson-dev libopencv-dev \
  libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
  gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl

set +u
# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash
set -u

log "Configuring rosdep"
if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  sudo rosdep init
fi
if [[ ! -f /etc/ros/rosdep/sources.list.d/00-gazebo.list ]]; then
  sudo wget -q \
    https://raw.githubusercontent.com/osrf/osrf-rosdep/master/gz/00-gazebo.list \
    -O /etc/ros/rosdep/sources.list.d/00-gazebo.list
fi
rosdep update

log "Installing ArduPilot in $ARDUPILOT_DIR"
if [[ ! -d "$ARDUPILOT_DIR/.git" ]]; then
  [[ ! -e "$ARDUPILOT_DIR" ]] || fail "$ARDUPILOT_DIR exists and is not a Git repository."
  git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git "$ARDUPILOT_DIR"
fi
cd "$ARDUPILOT_DIR"
git checkout Copter-4.7.0
git submodule update --init --recursive
Tools/environment_install/install-prereqs-ubuntu.sh -y

# Activate the ArduPilot virtual environment if its helper created one.
if [[ -f "$HOME/venv-ardupilot/bin/activate" ]]; then
  set +u
  # shellcheck disable=SC1091
  source "$HOME/venv-ardupilot/bin/activate"
  set -u
fi

./waf configure --board sitl
./waf copter

log "Installing ArduPilot Gazebo in $ARDUPILOT_GAZEBO_DIR"
if [[ ! -d "$ARDUPILOT_GAZEBO_DIR/.git" ]]; then
  [[ ! -e "$ARDUPILOT_GAZEBO_DIR" ]] || fail "$ARDUPILOT_GAZEBO_DIR exists and is not a Git repository."
  git clone https://github.com/ArduPilot/ardupilot_gazebo.git "$ARDUPILOT_GAZEBO_DIR"
fi
cd "$ARDUPILOT_GAZEBO_DIR"
git checkout ros2
rosdep install --from-paths . --ignore-src -r -y --rosdistro humble
GZ_VERSION=harmonic cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
GZ_VERSION=harmonic cmake --build build --parallel "$(nproc)"

log "Installing MAVROS datasets and downloading LRS-URK Git LFS files"
sudo bash -c \
  'source /opt/ros/humble/setup.bash && ros2 run mavros install_geographiclib_datasets.sh'
git lfs install
git -C "$LRS_URK_DIR" lfs pull

log "Adding paths to $BASHRC"
touch "$BASHRC"
TMP_BASHRC="$(mktemp)"
awk -v start="$ENV_START" -v end="$ENV_END" '
  $0 == start { skip = 1; next }
  $0 == end   { skip = 0; next }
  !skip       { print }
' "$BASHRC" > "$TMP_BASHRC"
cat "$TMP_BASHRC" > "$BASHRC"
rm -f "$TMP_BASHRC"

cat >> "$BASHRC" <<EOF

$ENV_START
source /opt/ros/humble/setup.bash
export ARDUPILOT_DIR="$ARDUPILOT_DIR"
export ARDUPILOT_GAZEBO_DIR="$ARDUPILOT_GAZEBO_DIR"
export LRS_URK_DIR="$LRS_URK_DIR"
export GZ_VERSION=harmonic
export PATH="\$ARDUPILOT_DIR/Tools/autotest:\$PATH"
export GZ_SIM_SYSTEM_PLUGIN_PATH="\$ARDUPILOT_GAZEBO_DIR/build:\${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"
export GZ_SIM_RESOURCE_PATH="\$ARDUPILOT_GAZEBO_DIR/models:\$ARDUPILOT_GAZEBO_DIR/worlds:\$LRS_URK_DIR/models:\${GZ_SIM_RESOURCE_PATH:-}"
$ENV_END
EOF

log "Installation finished"
printf 'ArduPilot:        %s\n' "$ARDUPILOT_DIR"
printf 'ArduPilot Gazebo: %s\n' "$ARDUPILOT_GAZEBO_DIR"
printf 'Run: source %s\n' "$BASHRC"
printf 'Thank you for choosing the edisimo express installation\n'
printf 'PLEASE REBOOT YOUR PC\n'
