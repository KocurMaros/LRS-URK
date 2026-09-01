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
- `exams/` — the semester's assignments: how the semester works, grading and deadlines
  in [`exams/README.md`](exams/README.md), the assignments themselves in
  [`exams/exam1/`](exams/exam1/) and [`exams/exam2/`](exams/exam2/).

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
