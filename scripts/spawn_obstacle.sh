#!/bin/bash
# Spawn (or remove) a static, orange box obstacle in the running gz sim world.
#
# Usage:
#   scripts/spawn_obstacle.sh NAME X Y [WIDTH] [DEPTH] [HEIGHT] [YAW]
#   scripts/spawn_obstacle.sh --remove NAME
#
#   NAME    unique model name, e.g. obstacle_1
#   X Y     position of the box centre in Gazebo world coordinates (metres),
#           not your MAVROS local ENU frame
#   WIDTH   size along the world Y axis, metres (default 0.6)
#   DEPTH   size along the world X axis, metres (default 0.6)
#   HEIGHT  size along Z, metres (default 3.0); the box always stands on the floor
#   YAW     rotation about Z, radians (default 0)
#
# Examples:
#   scripts/spawn_obstacle.sh obstacle_1 16 7            # 0.6 x 0.6 x 3 m box
#   scripts/spawn_obstacle.sh wall_1 16 7 2 0.6 2.5      # 2 m wide, 0.6 m deep, 2.5 m tall
#   scripts/spawn_obstacle.sh --remove obstacle_1
#
# The world is detected from the running simulation; set GZ_WORLD to choose one
# explicitly if more than one world is running.
set -euo pipefail

usage() {
  sed -n '4,19p' "$0" | sed 's/^# \{0,1\}//' >&2
  exit "${1:-1}"
}

die() { echo "Error: $*" >&2; exit 1; }

is_number() { [[ "$1" =~ ^-?([0-9]+\.?[0-9]*|\.[0-9]+)$ ]]; }
is_positive() { is_number "$1" && awk -v v="$1" 'BEGIN { exit !(v > 0) }'; }

find_world() {
  if [[ -n "${GZ_WORLD:-}" ]]; then
    echo "$GZ_WORLD"
    return
  fi
  local worlds
  worlds="$(gz service -l 2>/dev/null | sed -n 's#^/world/\([^/]*\)/create$#\1#p' || true)"
  [[ -n "$worlds" ]] || die "no running gz sim world found. Start one first, e.g. scripts/run_gazebo.sh fei_lrs_gazebo_depth.world"
  [[ "$(wc -l <<<"$worlds")" -eq 1 ]] || die "several worlds are running ($(tr '\n' ' ' <<<"$worlds")); set GZ_WORLD to pick one"
  echo "$worlds"
}

model_exists() {
  # Read the whole list first: grep -q in a pipeline can end it early and, with
  # pipefail, turn a match into a failure.
  local models
  models="$(gz model --list 2>/dev/null | sed -n 's/^ *- //p' || true)"
  grep -qx -- "$1" <<<"$models"
}

call_service() {
  # gz service prints "data: true" on success
  local service="$1" reqtype="$2" req="$3" reply
  reply="$(gz service -s "$service" --reqtype "$reqtype" --reptype gz.msgs.Boolean \
    --timeout 3000 --req "$req" 2>&1)" || die "gz service call to $service failed: $reply"
  grep -q 'data: true' <<<"$reply" || die "$service did not succeed: ${reply:-no reply}"
}

[[ $# -ge 1 ]] || usage
[[ "$1" == "-h" || "$1" == "--help" ]] && usage 0

if [[ "$1" == "--remove" ]]; then
  [[ $# -eq 2 ]] || usage
  name="$2"
  world="$(find_world)"
  model_exists "$name" || die "no model named '$name' in world '$world'"
  call_service "/world/$world/remove" gz.msgs.Entity "name: \"$name\", type: MODEL"
  echo "Removed '$name' from world '$world'."
  exit 0
fi

[[ "$1" != -* && $# -ge 3 && $# -le 7 ]] || usage
name="$1" x="$2" y="$3"
width="${4:-0.6}" depth="${5:-0.6}" height="${6:-3.0}" yaw="${7:-0}"

[[ "$name" =~ ^[A-Za-z0-9_]+$ ]] || die "NAME may only contain letters, digits and underscores"
is_number "$x" || die "X must be a number, got '$x'"
is_number "$y" || die "Y must be a number, got '$y'"
is_number "$yaw" || die "YAW must be a number, got '$yaw'"
for pair in "WIDTH:$width" "DEPTH:$depth" "HEIGHT:$height"; do
  is_positive "${pair#*:}" || die "${pair%%:*} must be a positive number, got '${pair#*:}'"
done

world="$(find_world)"
# gz answers "data: true" even when it refuses a duplicate name, so check first.
model_exists "$name" && die "a model named '$name' already exists; pick another name or remove it with --remove $name"

z="$(awk -v h="$height" 'BEGIN { printf "%g", h / 2 }')"   # centre at half height: box stands on the floor
size="$depth $width $height"
colour="1 0.4 0 1"

sdf="<sdf version='1.9'><model name='$name'><static>true</static>"
sdf+="<pose>$x $y $z 0 0 $yaw</pose><link name='link'>"
sdf+="<collision name='collision'><geometry><box><size>$size</size></box></geometry></collision>"
sdf+="<visual name='visual'><geometry><box><size>$size</size></box></geometry>"
sdf+="<material><ambient>$colour</ambient><diffuse>$colour</diffuse></material></visual>"
sdf+="</link></model></sdf>"

call_service "/world/$world/create" gz.msgs.EntityFactory "sdf: \"$sdf\""
model_exists "$name" || die "Gazebo accepted the request but '$name' did not appear; check the Gazebo terminal"
echo "Spawned '$name' in world '$world': ${width} m wide (Y) x ${depth} m deep (X) x ${height} m tall at ($x, $y), yaw $yaw rad."
