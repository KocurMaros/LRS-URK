# Obstacle avoidance (10 points)

One of the three [Assignment 2](README.md) topics. **Deadline: end of week 12.** See
[`../README.md`](../README.md) for the semester rules and [`README.md`](README.md) for the
rules shared by all three topics (threshold, documentation, git).

## What you are building

Your drone flies from point A to point B along a straight line. Somewhere along that line
there is an obstacle it did not know about when the mission started. You detect it from the
depth camera, decide where to go instead, and fly around it — then carry on to B.

This extends the control node from [Assignment 1](../assignment1/README.md): same node, same MAVROS
setpoints, same position controller. What's new is a perception input (the point cloud) feeding
a decision (replan) back into the thing you already built.

Fly it in the hangar world with the depth camera:
`worlds/fei_lrs_gazebo_depth.world`. It carries a native `rgbd_camera` sensor on the drone
(link `fei_lrs_drone/stereo_cam_link`, gz-transport base topic `fei_lrs_drone/stereo_camera`)
publishing colour, depth and — already computed for you — a point cloud. Bring it up like the
other worlds, by hand, per the [repository README](../../README.md):

```bash
gz sim worlds/fei_lrs_gazebo_depth.world
```

### Getting the point cloud into ROS 2

The sensor publishes on **gz-transport**, not ROS 2 — you bridge the topics you need with
`ros_gz_bridge`:

```bash
ros2 run ros_gz_bridge parameter_bridge \
  /fei_lrs_drone/stereo_camera/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked \
  /fei_lrs_drone/stereo_camera/image@sensor_msgs/msg/Image[gz.msgs.Image \
  /fei_lrs_drone/stereo_camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo
```

The `[` means one-directional, gz → ROS — that's all you need for a sensor. After this,
`ros2 topic list` should show:

```
/fei_lrs_drone/stereo_camera/points
/fei_lrs_drone/stereo_camera/image
/fei_lrs_drone/stereo_camera/camera_info
```

Check it in RViz before writing a line of code: `rviz2`, set **Fixed Frame** to
`fei_lrs_drone/fei_lrs_drone/stereo_cam_link/stereo_camera_depth`, add a `PointCloud2` display
on the `/points` topic. If you see the hangar in 3D, you're ready to subscribe from your own
node.

That frame name looks doubled because it is: gz sim derives it from
`<model>/<link>/<sensor>`, and the link itself is already named `fei_lrs_drone/stereo_cam_link`
in the world file, so `fei_lrs_drone` ends up prefixed twice. Check `ros2 topic echo
/fei_lrs_drone/stereo_camera/points --field header.frame_id` if RViz shows nothing and you
suspect a frame mismatch — this is the value your own node's TF handling needs too.

## Specification

### 1. Point cloud subscriber — 2.0 points

- Subscribe to `/fei_lrs_drone/stereo_camera/points` (`sensor_msgs/msg/PointCloud2`) from a ROS
  2 node.
- Use `rclcpp::SensorDataQoS()` — this is a sensor topic, and the default reliable QoS will
  leave your callback silently empty. (See
  [`tutorial/ros2_cheatsheet.md`](../../tutorial/ros2_cheatsheet.md#step-2--subscriber) if that
  bites you.)
- Iterate the cloud and get usable 3D points out of it. `sensor_msgs::PointCloud2Iterator` is
  the standard tool for this — look it up. Iterating the raw byte layout yourself is also fine
  if you'd rather understand it at that level; no more detail than this is given on purpose,
  working out the message layout is part of the assignment.

**Accepted when:** you can print, for an arbitrary frame, the number of points received and the
range of their coordinates.

### 2. Obstacle detection — 3.0 points

Turn "here is a cloud of points" into "there is an obstacle at (x, y, z), yes or no."

- Filter the cloud down to what matters: points inside your flight corridor and inside a
  sensible range (the sensor's simulated clip is 2 cm–300 m with light Gaussian noise —
  discard clearly-noise readings, e.g. anything implausibly close).
- Decide on an **obstacle threshold distance** — the point at which "something is ahead" becomes
  "stop and replan." Don't pick it arbitrarily: derive it from your cruise speed and the
  distance you need to react and turn, the same way [A1.1](../assignment1/01_map_and_path_planning.md)
  derives its inflation radius from the drone's size plus a margin. Write the derivation down.
- **Detection must be stable.** A single stray point should not trigger a replan, and a real
  obstacle should not need ten attempts to notice. A simple approach that works well: require
  the same region to read "occupied" across several consecutive frames before you act on it.
  Some false positives are tolerated; noisy, flickering detections are not.
- **Report it in a way that's checkable**, not just a `std::cout` line: log it with
  `RCLCPP_WARN` including the obstacle's coordinates, and — recommended, not required —
  publish a `visualization_msgs/msg/Marker` at the detected point so it shows up in RViz next
  to your point cloud. This is worth doing even though it isn't scored directly: it is by far
  the fastest way to convince yourself (and, later, your teacher) that detection is correct.

**Accepted when:** you can place an obstacle in the drone's path and get a stable, correctly
positioned detection, with no detections when the path is clear.

### 3. Path replanning — 2.5 points

Once you know there's an obstacle, decide where to fly instead.

- Generate a new target point that clears the obstacle by your safety margin.
- **Check that the new point is actually free before you commit to it** — the same lesson as
  the hangar's shelving racks in A1.1: a point that merely "looks clear" because nothing was
  detected there yet is not the same as a point that has been verified clear. A rule like "step
  90° to the last known-clear side, by margin + obstacle radius" is enough; nothing here
  requires full 3D planning.
- A preprogrammed manoeuvre (step sideways, step up, back off) is an acceptable strategy — the
  assignment does not require a general planner. More adaptive strategies (aiming for the
  clearest direction in the cloud, going around vs. over depending on obstacle shape) are
  welcome and are the way to make this section robust rather than merely working once.
- This section can be demonstrated **without flying**: show the replanned point given a
  recorded or a live cloud, and show it is collision-free.

**Accepted when:** given an obstacle placed where you have not tested before, your node
produces a specific, verified-clear (x, y, z) to fly to.

### 4. Flight with replanning — 2.5 points

Put it together: fly the straight line from A to B, detect the obstacle in flight, replan, fly
around it, and continue to B — autonomously, no manual intervention after start.

- You may assume the drone starts already at point A — you do not have to fly there first.
- The path between A and B is a straight line; the obstacle sits on it.
- After clearing the obstacle, the drone must resume progress toward B, not stop at the
  avoidance point.

**Accepted when:** the complete A → B flight, with a previously-unseen obstacle placement,
succeeds unattended and without a collision.

## Point staging

The four sections above are also staged milestones — each one only pays out if the ones before
it are demonstrated, per the [Assignment 2 rules](README.md#rules-common-to-all-topics):

| Demonstrated | Points | % |
|---|---|---|
| §1 only | 2.0 | 20 % |
| §1 + §2 (stable detection) | 5.0 | 50 % |
| §1 + §2 + §3 (verified replan point, not flown) | 7.5 | 75 % |
| All four (flown, autonomous) | 10.0 | 100 % |

50 % is the pass mark for this topic on its own. The actual gate to sit the final test is on
**Assignment 1 + Assignment 2 combined** (56 % of 30, ≥ 16.8 — see
[`../README.md`](../README.md#grading)), not a per-topic minimum, so whether §1+§2 alone is
enough depends on what you scored on Assignment 1.

## Hints

- **Get the pipeline working with a static drone first.** Hover in place, put an obstacle in
  front of the camera, confirm detection and the replanned point in RViz. Only then put it in
  motion. Debugging perception and flight control at the same time is much harder than either
  alone.
- **Record a rosbag of the point cloud** (`ros2 bag record /fei_lrs_drone/stereo_camera/points`)
  once your detector is halfway working. Replaying a bag is far faster to iterate on than
  restarting Gazebo every time.
- The depth image is genuinely noisy — that's the simulated sensor's Gaussian noise, not a bug
  in your code. Filtering has to tolerate it; don't chase a threshold that only works on a
  noise-free frame.
- Keep the obstacle-detection code and the flight-control code in **separate callback groups**
  (see [`mt_executor_demo`](../../mt_executor_demo/README.md)) — a cloud with hundreds of
  thousands of points takes real processing time, and it must never stall your setpoint
  publisher.

## Deliverables

- ROS 2 package(s) building with `colcon build`, extending your Assignment 1 control node.
- The `ros_gz_bridge` command(s) needed, documented in your README.
- Documentation per [`README.md`](README.md#rules-common-to-all-topics): your detection
  threshold and how you derived it, your replanning strategy, pros/cons, a diagram of the
  perception → decision → control data flow.
- Rosbag or screen recording of a complete A → B flight with an obstacle in the path.

## Links

- [`useful_links.md`](../assignment1/useful_links.md) — MAVROS/MAVLink references, general tooling
- [`tutorial/ros2_cheatsheet.md`](../../tutorial/ros2_cheatsheet.md) — subscribers, QoS, callback groups
- [`ros_gz` bridge](https://github.com/gazebosim/ros_gz) — `parameter_bridge` usage and the full gz ↔ ROS type table
- [PCL tutorials](https://pcl.readthedocs.io/projects/tutorials/en/latest/) — if you'd rather
  process the cloud with PCL than iterate it by hand
- [`sensor_msgs::PointCloud2Iterator` header](https://github.com/ros2/common_interfaces/blob/rolling/sensor_msgs/include/sensor_msgs/point_cloud2_iterator.hpp)
- [`visualization_msgs/msg/Marker`](https://docs.ros2.org/latest/api/visualization_msgs/msg/Marker.html) — for showing a detected obstacle in RViz
