# mt_executor_demo

A minimal C++ example of `rclcpp::executors::MultiThreadedExecutor`: several
independent workloads run concurrently on separate threads instead of
queuing behind one another, which is what happens with the default
`SingleThreadedExecutor`.

## Why this matters

A single-threaded ROS 2 node processes every timer and subscription callback
one at a time, in whatever order they become ready. If one callback is slow
(say, a vision pipeline crunching a frame), every other callback — including
a time-critical one like IMU processing — waits behind it.

`MultiThreadedExecutor` fixes this by dispatching callbacks from a thread
pool. Put callbacks that must never block each other into separate
**callback groups**, add the node to the executor, and the executor runs
those groups concurrently.

## What this node does

`mt_executor_demo_node` registers four callbacks, each in its own
`MutuallyExclusive` callback group:

| Callback         | Group             | Rate   | Purpose                                             |
|------------------|-------------------|--------|------------------------------------------------------|
| `imu_sim_tick`    | `imu_sim_group_`    | 100 Hz | Synthetic fast workload, no external dependency      |
| `vision_sim_tick` | `vision_sim_group_` | 10 Hz  | Synthetic slow workload (30 ms artificial delay/call) |
| `mavros_imu_cb`   | `mavros_imu_group_` | —      | Real subscription: `mavros/imu/data` (`sensor_msgs/Imu`) |
| `mavros_pose_cb`  | `mavros_pose_group_`| —      | Real subscription: `mavros/local_position/pose` (`geometry_msgs/PoseStamped`) |

The two synthetic timers make the concurrency visible without needing
anything else running: `vision_sim_tick` deliberately blocks for 30 ms on
every call, yet `imu_sim_tick` still reaches its 100th call at almost exactly
the 1-second mark, proving it isn't waiting on the slow callback. Each log
line also prints `std::this_thread::get_id()` — you'll see different thread
IDs across callbacks, which is the executor's thread pool at work.

The two MAVROS subscriptions plumb into whatever this course's SITL setup
publishes (see the [repo README](../README.md) for how to bring up
Gazebo + ArduPilot SITL + MAVROS). Note this package depends only on
`sensor_msgs` and `geometry_msgs`, not `mavros_msgs` — `Imu` and
`PoseStamped` are the plain message types MAVROS publishes on those topics,
so the node builds and runs standalone even without MAVROS installed; the
two subscriptions just won't receive anything until `mavros_node` is up.

## Build

From a ROS 2 workspace (tested on ROS 2 Jazzy):

```bash
mkdir -p ~/ros2_ws/src
ln -s /path/to/LRS-URK/mt_executor_demo ~/ros2_ws/src/
cd ~/ros2_ws
colcon build --packages-select mt_executor_demo
source install/setup.bash
```

## Run

```bash
ros2 run mt_executor_demo mt_executor_demo_node
```

You should immediately see interleaved `[imu_sim]` and `[vision_sim]` log
lines on different thread IDs. If MAVROS is running against the SITL setup,
`[mavros_imu]` and `[mavros_pos]` lines join in as telemetry arrives.

## Try it single-threaded

To see the problem this solves, swap `rclcpp::executors::MultiThreadedExecutor`
for `rclcpp::executors::SingleThreadedExecutor` in `main()`, rebuild, and run
again — `imu_sim` will now visibly stall behind `vision_sim`'s 30 ms delay
instead of ticking smoothly at 100 Hz.
