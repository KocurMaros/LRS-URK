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
- `scripts/` — launch scripts for each piece (`run_gazebo.sh`, `run_sitl.sh`,
  `run_mavros.sh`); see [Running the simulation](#running-the-simulation).

## Prerequisites

- `gz sim` (Gazebo Sim). Tested against both **Jetty** (10.x, the plain
  system install on Ubuntu 24.04) and **Harmonic** (8.x, ROS 2 Jazzy's
  officially supported pairing — see the version note below).
- The [ardupilot_gazebo](https://github.com/ArduPilot/ardupilot_gazebo)
  plugin, built against whichever Gazebo version you're running and
  discoverable via `GZ_SIM_SYSTEM_PLUGIN_PATH`.
- ArduPilot SITL (`arducopter`), built with `./waf configure --board sitl && ./waf copter`.
- ROS 2 (tested on Jazzy) if you want to build `mt_executor_demo` or bridge
  Gazebo topics into ROS 2 with `ros_gz_bridge`.

### A note on Gazebo versions

Per the [official compatibility table](https://gazebosim.org/docs/latest/ros_installation/),
ROS 2 Jazzy only supports **Gazebo Harmonic** — Jetty is marked incompatible.
If you `apt install ros-jazzy-ros-gz` on a machine that already has system
Gazebo Jetty installed, it pulls in `ros-jazzy-gz-sim-vendor`, which
**compiles and bundles its own separate copy of Harmonic** rather than
reusing Jetty, and `/opt/ros/jazzy/setup.bash` quietly points `GZ_CONFIG_PATH`
/`LD_LIBRARY_PATH` at it — so plain `gz sim` silently switches versions
after sourcing ROS's setup script, even though `which gz`/`gz sim --version`
can look unchanged depending on how you check.

Both worlds in this repo, and the `ardupilot_gazebo` plugin, work fine
against either version — they just need to be built and pointed at
consistently. To build the plugin against the ROS-vendored Harmonic instead
of system Jetty:

```bash
source /opt/ros/jazzy/setup.bash
cd ardupilot_gazebo && mkdir build-harmonic && cd build-harmonic
GZ_VERSION=harmonic cmake .. -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_INSTALL_PREFIX=<install-dir>
cmake --build . -j$(nproc) && cmake --install .
```

Then point `GZ_SIM_SYSTEM_PLUGIN_PATH` at
`<install-dir>/lib/ardupilot_gazebo` when running under Harmonic
(`GZ_CONFIG_PATH`/`LD_LIBRARY_PATH` as set by ROS's `setup.bash`), or at the
Jetty build's plugin directory with those two variables unset/pointing at
system paths when running plain Jetty.

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
