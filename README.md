# LRS-URK

Gazebo Sim (`gz sim`) worlds, models, and a ROS 2 example, migrated from the
classic-Gazebo [LRS-FEI](https://github.com/KocurMaros/LRS-FEI) setup to run
on `gz sim` with ArduPilot SITL via the
[ardupilot_gazebo](https://github.com/ArduPilot/ardupilot_gazebo) plugin.

## Contents

- `worlds/fei_lrs_gazebo.world` — the FEI hangar world with a quadcopter
  (stereo camera, IMU, ArduPilot flight controller bridge).
- `worlds/fei_lrs_gazebo_depth.world` — same world, with the drone's camera
  swapped for a native `rgbd_camera` sensor (color + depth + point cloud).
- `models/` — the mesh/material assets those two worlds depend on. The
  `fei_lrs_hangar` and `fei_lrs_racks` model directories contain generated
  Harmonic-compatible SDF around the original `hangar` meshes.
- `mt_executor_demo/` — a ROS 2 C++ example of `MultiThreadedExecutor`;
  see its own [README](mt_executor_demo/README.md).
- `tutorial/ros2_cheatsheet.md` — ROS 2 workspace layout, console commands, and getting a
  topic from `ros2 topic echo` into your C++ node.
- `scripts/` — launch scripts for each piece (`run_gazebo.sh`, `run_sitl.sh`,
  `run_mavros.sh`); see [Running the simulation](#running-the-simulation).
- `assignments/` — the semester's assignments: how the semester works, grading and deadlines
  in [`assignments/README.md`](assignments/README.md), the assignments themselves in
  [`assignments/assignment1/`](assignments/assignment1/) and [`assignments/assignment2/`](assignments/assignment2/).

## Prerequisites

- Ubuntu 22.04 or Ubuntu 24.04.
- An internet connection and Git, to clone this repository.
- A normal user account with `sudo` access. Do not run the installer as root.

## Installation

Clone the repository and run the installer as your normal user:

```bash
git clone https://github.com/KocurMaros/LRS-URK.git
cd LRS-URK
scripts/install.sh
```

The script detects the supported Ubuntu version and installs the matching ROS
2 distribution (Humble on 22.04 or Jazzy on 24.04), Gazebo Harmonic,
ArduPilot SITL, `ardupilot_gazebo`, MAVROS, and the required dependencies. It
also adds the required environment variables to `~/.bashrc`. Reboot after the
installation finishes.

To remove ArduPilot, `ardupilot_gazebo`, their virtual environment, and the
shell configuration added by the installer, run:

```bash
scripts/install.sh --uninstall
```

To also remove the ROS, Gazebo, MAVROS, and related packages installed by the
script, run:

```bash
scripts/install.sh --purge
```

## Running the simulation

Three terminals, one script each:

```bash
# Terminal 1 — Gazebo. Defaults to fei_lrs_gazebo.world; pass a filename
# from worlds/ to run the depth-camera variant instead.
scripts/run_gazebo.sh
scripts/run_gazebo.sh fei_lrs_gazebo_depth.world

# Terminal 2 — ArduPilot SITL, bridged to whatever Gazebo instance is running.
# ARDUPILOT_DIR defaults to $HOME/ardupilot; override if yours lives elsewhere.
scripts/run_sitl.sh

# Terminal 3 — MAVROS, bridged to SITL.
scripts/run_mavros.sh
```

Under the hood, `run_sitl.sh` runs:

```bash
cd ardupilot/ArduCopter
sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON \
  --add-param-file=$HOME/ardupilot/Tools/autotest/default_params/gazebo-iris.parm \
  --console -l 48.15084570555732,17.072729745416016,150,0
```

The frame must stay `gazebo-iris` (it only selects default parameters —
motor count, frame class/type) but `--model JSON` must be passed explicitly
so SITL talks the JSON/FDM protocol the `ardupilot_gazebo` plugin expects,
instead of the legacy protocol classic Gazebo's `ArduPilotPlugin` used. The
`--add-param-file` is required alongside it: current `sim_vehicle.py` no
longer auto-loads a frame's default param file once `--model` is overridden
away from the frame name, so without it `FRAME_CLASS` stays `0` (undefined)
and the vehicle refuses to arm ("Check frame class and type").

## A note on Gazebo versions

This repository uses **Gazebo Harmonic**. It works well with both ROS 2 Humble and Jazzy, and it
is what `scripts/install.sh` installs on both Ubuntu versions, together with an
`ardupilot_gazebo` plugin built against it. Gazebo **Jetty** is not supported by us — it should
work in theory, but if you use it you are on your own.

If you have more than one Gazebo version installed, `gz sim` can start a different one than the
`ardupilot_gazebo` plugin was built for. That shows up as a plugin error or a silently missing
drone, not as an obvious version message. `scripts/run_gazebo.sh` prints the version it starts
(`gz sim version: ...`) — check that line first. If it is not Harmonic, make sure the
`ardupilot_gazebo` build matching that version is on `GZ_SIM_SYSTEM_PLUGIN_PATH`.

## Connecting to the real drone

When you fly outdoors on the real drone (see
[`assignments/README.md`](assignments/README.md#flying-the-real-drone) for when that is
allowed), your laptop talks to the drone's ROS 2 over the network using CycloneDDS. Your laptop
has to be on the drone's network, able to reach `192.168.88.250`.

Install CycloneDDS once:

```bash
sudo apt install ros-$ROS_DISTRO-rmw-cyclonedds-cpp
```

`$ROS_DISTRO` is set by the ROS setup line the installer adds to `~/.bashrc` (`humble` on
Ubuntu 22.04, `jazzy` on 24.04), so the same command works on both.

Then set the environment and check that the drone is visible:

```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI='<CycloneDDS><Domain Id="any"><Discovery><ParticipantIndex>auto</ParticipantIndex><Peers><Peer Address="192.168.88.250"/></Peers></Discovery></Domain></CycloneDDS>'
ros2 daemon stop; ros2 topic list
```

- `RMW_IMPLEMENTATION` switches ROS 2 in this terminal to CycloneDDS.
- `CYCLONEDDS_URI` adds the drone (`192.168.88.250`) as a discovery peer, so your laptop
  contacts it directly instead of relying on multicast discovery alone. `ParticipantIndex auto`
  lets several ROS 2 processes on your laptop run side by side.
- `ros2 daemon stop` throws away the ROS 2 CLI daemon started with the old settings; the next
  `ros2` command starts a fresh one. `ros2 topic list` should then show the drone's `/droneX/...`
  topics — see [Topic names on the real drone](#topic-names-on-the-real-drone).

The two `export` lines only apply to the terminal you run them in. So that you don't have to
repeat them in every terminal, append them to your `~/.bashrc` once:

```bash
cat >> ~/.bashrc <<'EOF'
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI='<CycloneDDS><Domain Id="any"><Discovery><ParticipantIndex>auto</ParticipantIndex><Peers><Peer Address="192.168.88.250"/></Peers></Discovery></Domain></CycloneDDS>'
EOF
```

Every new terminal then picks them up — open a new one (or `source ~/.bashrc`) and run
`ros2 daemon stop` once. From then on the simulation also runs on CycloneDDS; that is fine, as
long as every ROS 2 process uses the same middleware. To go back to the default, delete the two
lines from `~/.bashrc`.

### Topic names on the real drone

On the real drone, MAVROS does not run under `/mavros`. Every MAVROS topic and service is under
`/droneX` instead, where X is the number of the drone you fly — your teacher tells you which one.
For drone 10:

| Simulation | Real drone 10 |
|---|---|
| `/mavros/state` | `/drone10/state` |
| `/mavros/global_position/local` | `/drone10/global_position/local` |
| `/mavros/setpoint_raw/local` | `/drone10/setpoint_raw/local` |
| `/mavros/cmd/arming` | `/drone10/cmd/arming` |

Don't hardcode `/mavros` in your nodes — make the prefix a parameter, so the same code runs in
the simulation and on the drone.

## Notes on the migration from classic Gazebo

- `libArduPilotPlugin.so` / `libLiftDragPlugin.so` (classic Gazebo plugins)
  were replaced with `gz sim`'s native `ArduPilotPlugin` and
  `gz-sim-lift-drag-system`.
- The stereo `multicamera` sensor (driven by `libgazebo_ros_camera.so`, a
  classic-Gazebo-only ROS bridge) was split into two native `camera`
  sensors publishing directly over `gz-transport` — see `worlds/fei_lrs_gazebo.world`.
  The depth variant uses a single native `rgbd_camera` sensor instead.
- Harmonic's DART backend cannot use these Collada meshes as collision
  geometry. `scripts/generate_harmonic_models.py` reads each native `Z_UP`
  Collada node transform and creates a tight primitive box for every building
  and rack member, while retaining the detailed meshes for rendering. Rerun
  the script after changing a hangar mesh. This also avoids the axis conversion
  bug that previously placed the hangar collisions below the floor.
- The racks are a separate `fei_lrs_racks` model, exposed as
  `warehouse_racks` in Gazebo's entity tree. Their per-member collisions let
  boxes rest on the actual shelf boards instead of a coarse bounding volume.
- World-level system plugins (`Physics`, `Sensors`, `UserCommands`,
  `SceneBroadcaster`, `Imu`, `NavSat`) are declared explicitly, since `gz sim`
  — unlike classic Gazebo — doesn't load them implicitly.
