#!/usr/bin/env bash
set -euo pipefail

ARDUPILOT_DIR="${ARDUPILOT_DIR:-$HOME/ardupilot}"
ARDUPILOT_GAZEBO_DIR="${ARDUPILOT_GAZEBO_DIR:-$HOME/ardupilot_gazebo}"
BASHRC="$HOME/.bashrc"
ENV_START='# >>> LRS-URK >>>'
ENV_END='# <<< LRS-URK <<<'
PURGE_PACKAGES=0
ASSUME_YES=0

for option in "$@"; do
  case "$option" in
    --purge-packages) PURGE_PACKAGES=1 ;;
    -y|--yes) ASSUME_YES=1 ;;
    -h|--help)
      echo "Usage: scripts/uninstall_ubuntu_22.sh [--purge-packages] [--yes]"
      exit 0
      ;;
    *) echo "Unknown option: $option" >&2; exit 1 ;;
  esac
done

if (( ! ASSUME_YES )); then
  echo "This will remove:"
  echo "  $ARDUPILOT_DIR"
  echo "  $ARDUPILOT_GAZEBO_DIR"
  (( PURGE_PACKAGES )) && echo "  ROS/Gazebo/MAVROS packages installed by the installer"
  read -r -p "Continue? [y/N] " answer
  [[ "$answer" == y || "$answer" == Y ]] || exit 0
fi

rm -rf -- "$ARDUPILOT_DIR" "$ARDUPILOT_GAZEBO_DIR" "$HOME/venv-ardupilot"

if [[ -f "$BASHRC" ]]; then
  TMP_BASHRC="$(mktemp)"
  awk -v start="$ENV_START" -v end="$ENV_END" '
    $0 == start { skip = 1; next }
    $0 == end   { skip = 0; next }
    !skip       { print }
  ' "$BASHRC" > "$TMP_BASHRC"
  cat "$TMP_BASHRC" > "$BASHRC"
  rm -f "$TMP_BASHRC"
fi

# Remove the PATH / virtualenv lines added by ArduPilot's prerequisite script.
for SHELL_FILE in "$HOME/.profile" "$HOME/.bashrc"; do
  [[ -f "$SHELL_FILE" ]] || continue
  TMP_SHELL_FILE="$(mktemp)"
  awk -v ardupilot="$ARDUPILOT_DIR" -v venv="$HOME/venv-ardupilot" \
    'index($0, ardupilot) == 0 && index($0, venv) == 0 { print }' \
    "$SHELL_FILE" > "$TMP_SHELL_FILE"
  cat "$TMP_SHELL_FILE" > "$SHELL_FILE"
  rm -f "$TMP_SHELL_FILE"
done

if (( PURGE_PACKAGES )); then
  sudo apt remove -y ros-humble-desktop ros-dev-tools gz-harmonic ros-humble-ros-gzharmonic \
    ros-humble-mavros libgz-sim8-dev rapidjson-dev libopencv-dev \
    libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
    gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl
  sudo apt autoremove -y
fi

echo "Uninstall finished. Open a new terminal."
