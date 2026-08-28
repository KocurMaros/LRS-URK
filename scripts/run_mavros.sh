#!/bin/bash
# Launch mavros_node against the SITL instance started by run_sitl.sh.
# Matches the port sim_vehicle.py's default --out UDP endpoint uses.
set -euo pipefail

FCU_URL="${FCU_URL:-udp://127.0.0.1:14551@14555}"

exec ros2 run mavros mavros_node --ros-args -p fcu_url:="$FCU_URL"
