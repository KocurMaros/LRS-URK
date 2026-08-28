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
- `models/` — the mesh/material assets those two worlds depend on
  (`fei_lrs_drone`, `hangar`) — trimmed to only what's actually referenced.
- `mt_executor_demo/` — a ROS 2 C++ example of `MultiThreadedExecutor`;
  see its own [README](mt_executor_demo/README.md).

## Prerequisites

- `gz sim` (Gazebo Sim), tested against 10.x.
- The [ardupilot_gazebo](https://github.com/ArduPilot/ardupilot_gazebo)
  plugin, built and discoverable via `GZ_SIM_SYSTEM_PLUGIN_PATH`.
- ArduPilot SITL (`arducopter`), built with `./waf configure --board sitl && ./waf copter`.
- ROS 2 (tested on Jazzy) if you want to build `mt_executor_demo`.

## Running the simulation

Point Gazebo at this repo's models, then launch either world:

```bash
export GZ_SIM_RESOURCE_PATH=$(pwd)/models
gz sim worlds/fei_lrs_gazebo.world
```

In a second terminal, start ArduPilot SITL against it. The frame must stay
`gazebo-iris` (it only selects default parameters — motor count, frame
class/type) but `--model JSON` must be passed explicitly so SITL talks the
JSON/FDM protocol the `ardupilot_gazebo` plugin expects, instead of the
legacy protocol classic Gazebo's `ArduPilotPlugin` used:

```bash
cd ardupilot/ArduCopter
sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON \
  --add-param-file=$HOME/ardupilot/Tools/autotest/default_params/gazebo-iris.parm \
  --console -l 48.15084570555732,17.072729745416016,150,0
```

The `--add-param-file` is required: current `sim_vehicle.py` no longer
auto-loads a frame's default param file once `--model` is overridden away
from the frame name, so without it `FRAME_CLASS` stays `0` (undefined) and
the vehicle refuses to arm ("Check frame class and type").

Then, as before:

```bash
ros2 run mavros mavros_node --ros-args -p fcu_url:=udp://127.0.0.1:14551@14555
```

## Notes on the migration from classic Gazebo

- `libArduPilotPlugin.so` / `libLiftDragPlugin.so` (classic Gazebo plugins)
  were replaced with `gz sim`'s native `ArduPilotPlugin` and
  `gz-sim-lift-drag-system`.
- The stereo `multicamera` sensor (driven by `libgazebo_ros_camera.so`, a
  classic-Gazebo-only ROS bridge) was split into two native `camera`
  sensors publishing directly over `gz-transport` — see `worlds/fei_lrs_gazebo.world`.
  The depth variant uses a single native `rgbd_camera` sensor instead.
- The hangar model's mesh **collision** geometry (kept as detailed meshes
  for visuals) was replaced with axis-aligned bounding boxes computed from
  each mesh's true geometry (node transforms included, via `pyassimp`) —
  some of the original `.dae` files have malformed submeshes that crash
  `gz sim`'s DART/ODE mesh-collision path.
- World-level system plugins (`Physics`, `Sensors`, `UserCommands`,
  `SceneBroadcaster`, `Imu`, `NavSat`) are declared explicitly, since `gz sim`
  — unlike classic Gazebo — doesn't load them implicitly.
