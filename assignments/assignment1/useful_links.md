# Useful links and commands

Everything you need to operate the stack and look things up. Most of this is useful for
Assignment 2 as well. Bookmark the MAVROS plugin list and the MAVLink common message set — you will
open them constantly.

---

## 1. Running the stack

**Three terminals, brought up by hand** — the exact commands are in the
[repository README](../../README.md), section *Running the simulation*:

1. **Gazebo** — `gz sim` with the world from `worlds/` and `GZ_SIM_RESOURCE_PATH` pointing at
   `models/`.
2. **ArduPilot SITL** — `sim_vehicle.py`, with the arguments the README specifies. Read the
   note about `--model JSON` and `--add-param-file`; without them the vehicle will not arm and
   the error message does not point at the cause.
3. **MAVROS** — `mavros_node` with the `fcu_url` matching SITL's output port.

There is no script that does this for you, on purpose. When something does not work you need to
know which of the three processes to look at, and that only comes from starting them yourself.

Read the README's **"A note on Gazebo versions"** section before you debug a plugin that will
not load — Jetty vs. Harmonic is the most common setup problem in this course, and the symptom
(a silently missing drone or a plugin error) does not look like a version mismatch.

- [This repository's README](../../README.md) — setup, worlds, migration notes
- [`tutorial/ros2_cheatsheet.md`](../../tutorial/ros2_cheatsheet.md) — workspace layout, console
  commands, and how to get a topic into your C++ code
- [`mt_executor_demo`](../../mt_executor_demo/README.md) — the worked node example: callback
  groups and a multithreaded executor
- [Course drive folder](https://drive.google.com/drive/folders/1QdG5tw1aGTgOuVNYAXl9BhDGObsHb8TW?usp=sharing)

## 2. Commands you will use constantly

Flying by hand from the terminal — do this **before** writing any node:

```bash
ros2 service call /mavros/set_mode mavros_msgs/srv/SetMode "{base_mode: 0, custom_mode: GUIDED}"
ros2 service call /mavros/cmd/arming mavros_msgs/srv/CommandBool "{value: True}"
ros2 service call /mavros/cmd/takeoff mavros_msgs/srv/CommandTOL "{min_pitch: 0, yaw: 0, altitude: 2}"
ros2 service call /mavros/cmd/land mavros_msgs/srv/CommandTOL "{min_pitch: 0, yaw: 0, altitude: 0}"
```

Inspecting what is going on:

```bash
ros2 topic list                                     # what exists
ros2 topic echo /mavros/state                       # connected? armed? which mode?
ros2 topic echo /mavros/local_position/pose         # where am I (ENU, metres from origin)
ros2 topic echo /mavros/global_position/global      # where am I (lat/lon/alt)
ros2 topic echo /mavros/global_position/compass_hdg # heading, degrees from North, clockwise
ros2 topic hz /mavros/local_position/pose           # is it actually publishing?
ros2 interface show mavros_msgs/msg/PositionTarget  # the type_mask and frame constants
ros2 param list /mavros                             # MAVROS parameters
```

Recording evidence — run this before every mission:

```bash
ros2 bag record -a -o run_$(date +%F_%H%M%S)
ros2 bag play <bagdir>
```

Visualising:

```bash
rviz2          # trajectories, markers, point clouds
rqt_graph      # who talks to whom
```

## 3. MAVROS and MAVLink

The single most important reference for this course is the MAVROS plugin list — it names every
topic and service MAVROS offers, with its message type.

- **[MAVROS plugin list — all topics and services](http://wiki.ros.org/mavros/Plugins)**
- [MAVROS main page, including frame conventions](http://wiki.ros.org/mavros)
- [MAVROS source (ROS 2)](https://github.com/mavlink/mavros)
- [MAVLink common message set](https://mavlink.io/en/messages/common.html)
- [`SET_POSITION_TARGET_LOCAL_NED`](https://mavlink.io/en/messages/common.html#SET_POSITION_TARGET_LOCAL_NED)
- [`SET_POSITION_TARGET_GLOBAL_INT`](https://mavlink.io/en/messages/common.html#SET_POSITION_TARGET_GLOBAL_INT)
- [`POSITION_TARGET_TYPEMASK`](https://mavlink.io/en/messages/common.html#POSITION_TARGET_TYPEMASK) — **read this one properly**
- [`MAV_FRAME`](https://mavlink.io/en/messages/common.html#MAV_FRAME)

### The topics you will actually use

| Topic | Type | What it gives you |
|---|---|---|
| `/mavros/state` | `mavros_msgs/State` | connected, armed, current flight mode |
| `/mavros/local_position/pose` | `geometry_msgs/PoseStamped` | local position + orientation, **ENU** |
| `/mavros/local_position/velocity_local` | `geometry_msgs/TwistStamped` | velocity, ENU |
| `/mavros/global_position/global` | `sensor_msgs/NavSatFix` | lat / lon / AMSL altitude, fix status |
| `/mavros/global_position/local` | `nav_msgs/Odometry` | global fix expressed in local ENU |
| `/mavros/global_position/rel_alt` | `std_msgs/Float64` | altitude relative to home |
| `/mavros/global_position/compass_hdg` | `std_msgs/Float64` | heading, degrees from North, CW |
| `/mavros/home_position/home` | `mavros_msgs/HomePosition` | where home is |
| `/mavros/setpoint_raw/local` | `mavros_msgs/PositionTarget` | position/velocity/accel + yaw setpoints |
| `/mavros/setpoint_raw/global` | `mavros_msgs/GlobalPositionTarget` | the same, in lat/lon |
| `/mavros/setpoint_position/local` | `geometry_msgs/PoseStamped` | simple position setpoint |

Services: `/mavros/set_mode`, `/mavros/cmd/arming`, `/mavros/cmd/takeoff`, `/mavros/cmd/land`.

Do not trust this table blindly — confirm with `ros2 topic list` and `ros2 interface show`
against the MAVROS version actually installed on your machine.

### Frames — the thing that will bite you

| | X | Y | Z | Yaw zero | Yaw direction |
|---|---|---|---|---|---|
| **ENU** (ROS, MAVROS topics) | East | North | Up | East | counter-clockwise |
| **NED** (MAVLink, ArduPilot internally) | North | East | Down | North | clockwise |
| **Compass heading** | — | — | — | North | clockwise |

`yaw_ENU_deg = 90 - heading_deg`, wrapped into `(-180, 180]`.

MAVROS converts between ENU and NED for you on most topics — but **not everywhere, and not in
your own maths**. Print both and check, every time. A mirrored trajectory or a heading off by
90° is always this.

- [REP-103 — units and coordinate conventions](https://www.ros.org/reps/rep-0103.html)
- [REP-105 — coordinate frames for mobile platforms](https://www.ros.org/reps/rep-0105.html)

## 4. ArduPilot

- [Copter documentation](https://ardupilot.org/copter/index.html)
- [GUIDED mode](https://ardupilot.org/copter/docs/ac2_guidedmode.html)
- [Copter commands in GUIDED mode](https://ardupilot.org/dev/docs/copter-commands-in-guided-mode.html) — what the autopilot accepts and how it behaves
- [SITL — software in the loop](https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html)
- [SITL + MAVProxy tutorial](https://ardupilot.org/dev/docs/copter-sitl-mavproxy-tutorial.html)
- [Complete parameter list](https://ardupilot.org/copter/docs/parameters.html)
- [Failsafes](https://ardupilot.org/copter/docs/failsafe-landing-page.html)
- [Geofencing](https://ardupilot.org/copter/docs/common-geofencing-landing-page.html)
- [Compass calibration](https://ardupilot.org/copter/docs/common-compass-calibration-in-mission-planner.html)
- [MAVProxy](https://ardupilot.org/mavproxy/) — the console `run_sitl.sh` opens; `param show`,
  `param set`, `mode`, `arm throttle` all work there and are excellent for debugging
- [QGroundControl](https://qgroundcontrol.com/) / [Mission Planner](https://ardupilot.org/planner/) —
  ground stations; useful for watching what the vehicle thinks is happening

**When something will not arm, read the SITL console.** ArduPilot states the exact pre-arm
check that failed. It is never a mystery, and guessing wastes an afternoon.

## 5. Gazebo Sim

- [Gazebo Harmonic documentation](https://gazebosim.org/docs/harmonic/)
- [ROS ↔ Gazebo version compatibility table](https://gazebosim.org/docs/latest/ros_installation/) — read this before debugging anything
- [`ardupilot_gazebo` plugin](https://github.com/ArduPilot/ardupilot_gazebo) — also the source of the `iris_runway` world
- [`ros_gz` bridge](https://github.com/gazebosim/ros_gz) — getting Gazebo topics into ROS 2

## 6. ROS 2

- [ROS 2 Jazzy documentation](https://docs.ros.org/en/jazzy/index.html)
- [Tutorials — client libraries (writing nodes)](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries.html)
- [Parameters](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Parameters/Understanding-ROS2-Parameters.html) — use these instead of hardcoding
- [Executors and callback groups](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Executors.html)
  — and the worked example in [`mt_executor_demo`](../../mt_executor_demo/README.md) in this repository
- [`rclcpp` API reference](https://docs.ros.org/en/jazzy/p/rclcpp/)
- [tf2 tutorials](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Tf2-Main.html)
- [Quaternion fundamentals](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Quaternion-Fundamentals.html) — quaternion ↔ yaw, done right
- [Recording and playing back data (`ros2 bag`)](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Recording-And-Playing-Back-Data/Recording-And-Playing-Back-Data.html)
- [PlotJuggler](https://github.com/facontidavide/PlotJuggler) — plot topics live or from a bag;
  the fastest way to see whether your controller is oscillating

## 7. Maps, point clouds, planning

- [PCL tutorials](https://pcl.readthedocs.io/projects/tutorials/en/latest/) —
  [reading a PCD](https://pcl.readthedocs.io/projects/tutorials/en/latest/reading_pcd.html),
  [voxel grid](https://pcl.readthedocs.io/projects/tutorials/en/latest/voxel_grid.html),
  [octree](https://pcl.readthedocs.io/projects/tutorials/en/latest/octree.html)
- [Amit's A\* pages](https://theory.stanford.edu/~amitp/GameProgramming/) — the clearest explanation of A\* and heuristics anywhere
- [PathFinding.js visualiser](https://qiao.github.io/PathFinding.js/visual/) — play with A\*, Dijkstra, JPS in 2D
- [RRT explained in 2D](https://theclassytim.medium.com/robotic-path-planning-rrt-and-rrt-212319121378)
- [RRT / RRT\* in 3D](https://github.com/motion-planning/rrt-algorithms)
- [Path finder algorithms (reference implementations)](https://github.com/shkolovy/path-finder-algorithms)
- [OMPL](https://ompl.kavrakilab.org/) — production-grade planning library, if you want to integrate one
- [LaValle — *Planning Algorithms*](http://lavalle.pl/planning/) — the free textbook

## 8. GPS, geodesy, trajectories

- [GeographicLib](https://geographiclib.sourceforge.io/) — geodetic ↔ ECEF ↔ local ENU, done correctly
- [`geographic_info` / `geodesy` ROS packages](https://github.com/ros-geographic-info/geographic_info)
- [Local tangent plane coordinates](https://en.wikipedia.org/wiki/Local_tangent_plane_coordinates) — the flat-Earth approximation and when it is valid
- [Lemniscate of Gerono](https://en.wikipedia.org/wiki/Lemniscate_of_Gerono) — the figure-8 curve in A1.3
- [`atan2`](https://en.wikipedia.org/wiki/Atan2) — and why you need to unwrap its output

## 9. Getting help

Ask during the exercise, or write to your exercise teacher on **Teams**; consultation hours are
in **AIS**. See [`../README.md`](../README.md#consultations).

A good question includes: what you are trying to do, what you tried, the exact error message,
and the relevant few lines of code. A screenshot of a terminal beats "it does not work".
