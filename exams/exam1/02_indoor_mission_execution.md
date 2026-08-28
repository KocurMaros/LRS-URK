# E1.2 — Mission execution, indoor flight (6 points)

Take the path from [E1.1](01_map_and_path_planning.md) and actually fly it in the hangar
world, executing a task at each waypoint.

Bring the simulation up in **three terminals — by hand**, as described in the
[repository README](../../README.md): `gz sim` with the hangar world, ArduPilot SITL, and
MAVROS. There is no launch script that does it for you. Knowing which process is which, and
what each argument means, is part of the assignment — when the drone will not arm you need to
know which of the three to look at.

## The mission

A mission is a list of waypoints, each with a precision and a task. Example mission files are
in `missions/` in this repository.

| | X | Y | Z | Precision | Task |
|---|---|---|---|---|---|
| 1 | 13.60 | 1.50 | 1.00 | soft | takeoff |
| 2 | 8.65 | 2.02 | 1.00 | soft | - |
| 3 | 4.84 | 5.37 | 2.00 | hard | yaw180 |
| 4 | 2.08 | 9.74 | 1.75 | hard | - |
| 5 | 8.84 | 6.90 | 2.00 | hard | landtakeoff |
| 6 | 2.81 | 8.15 | 1.50 | soft | yaw90 |
| 7 | 13.60 | 1.50 | 2.00 | hard | land |

**These are goal waypoints, not a flight path.** Your planner from E1.1 has to find the
collision-free route *between* consecutive rows. The drone flies the planned path; the tasks
happen at the rows.

At the defence you will be given a **mission file you have not seen**, in this format.

## Specification

### 1. Control node and mission state machine — 1.5 points

- Load the mission from a **file given as a parameter or argument**. Not hardcoded, not
  recompiled per mission.
- A clear **state machine**: `IDLE → SET_MODE → ARM → TAKEOFF → NAVIGATE → TASK → … → LAND → DONE`,
  with the current state logged. When something goes wrong you want to see *where* it stopped.
- Handle the MAVROS handshake properly: wait for `/mavros/state` to report `connected`, set
  `GUIDED`, arm, and **check the responses**. Firing service calls into the void and hoping is
  the single most common reason a mission mysteriously does not start.
- Keep publishing setpoints at a steady rate (10–20 Hz is a safe default) rather than one
  message per waypoint.

The worked example for this course is
[`mt_executor_demo`](../../mt_executor_demo/README.md) in this repository. It shows the node
structure you want: subscriptions and timers split into **callback groups** running on a
`MultiThreadedExecutor`, so a slow callback cannot stall a time-critical one. That matters
here — your setpoint publisher must keep its rate while the planner is busy. Read its README,
run it, then swap in `SingleThreadedExecutor` to see what you are avoiding.

See also [`tutorial/ros2_cheatsheet.md`](../../tutorial/ros2_cheatsheet.md) for getting from
`ros2 topic echo` to a working subscriber in C++.

### 2. Position controller with hard/soft precision — 2.0 points

Fly to a point and know when you have arrived.

- **`hard`** — tight tolerance, the drone must genuinely settle at the point before continuing.
- **`soft`** — loose tolerance, the drone may pass through without stopping.
- Pick the actual numbers yourself and **justify them in the documentation**. A common choice
  is a small radius for `hard` and a larger one for `soft`; what matters is that the difference
  is visible in flight and defensible.
- "Arrived" should mean *arrived and stable*, not "the position error dipped below the
  threshold for one sample while flying past at 3 m/s". Think about velocity, or about
  requiring the condition to hold for some time.

**Accepted when:** at a `hard` waypoint the drone visibly stops and settles; at a `soft`
waypoint it does not. The difference must be obvious to the observer.

#### Do not stop at every point

Here is the trap. Your planner emits a *path* — possibly dozens of points. Your mission file
lists *waypoints* — seven of them. **These are not the same thing, and they must not be
treated the same way.**

If you apply a 10 cm acceptance radius to every point the planner produced, the drone stops at
every one of them, because the only way to reliably end up inside a 10 cm ball is to
decelerate into it. Forty path points become forty stop-and-go hops and a two-minute flight
across a room. This is the single most common way this sub-exam goes wrong.

Three things fix it, and you already have all three:

1. **Only mission waypoints carry a precision.** Intermediate path points are *pass-through*:
   use a generous acceptance radius — comparable to your voxel size or larger — and **never**
   require the velocity to reach zero. Send the next setpoint as soon as you are near enough;
   `GUIDED` position targets are latched, so the vehicle transitions smoothly instead of
   braking.
2. **Simplify the path** ([E1.1 §4](01_map_and_path_planning.md)). Fewer points, fewer chances
   to hesitate. This is why that section is worth a full point.
3. **`soft` vs `hard` is the whole mechanism.** `soft` means fly through without settling.
   `hard` means stop and settle — and stopping is *correct* there, because the next thing that
   happens is a task like `landtakeoff`.

For reference: something around 10–20 cm is a sensible `hard` tolerance in simulation. Pick
your numbers, measure what you actually achieve, and defend them in the documentation.

### 3. `takeoff` / `land` / `landtakeoff` — 1.5 points

- **`takeoff`** — arm and climb to the waypoint's Z. Confirm the drone is actually airborne
  before proceeding.
- **`land`** — descend and land safely at the waypoint, then disarm.
- **`landtakeoff`** — land at the waypoint, wait on the ground, then take off again and
  continue the mission. Watch out: after landing, ArduPilot may **disarm** — you have to
  re-arm and re-enter `GUIDED` before you can continue. This is the task that catches people.

### 4. `yaw <angle>` — 1.0 point

Rotate to a commanded heading at the waypoint and hold it.

- `yaw90`, `yaw180`, etc. — the number is the angle in degrees.
- Reach the heading, hold it, and only then continue.
- **Be explicit about the convention in your documentation:** is the angle relative to the
  world frame or to the current heading? Which direction is positive? ROS/MAVROS use **ENU**
  (X = East, yaw measured counter-clockwise from East) while MAVLink and ArduPilot use **NED**.
  Mixing them up is the classic bug here — it usually shows up as a heading mirrored or
  rotated by 90°.

#### The default heading is the direction of travel

A `yaw` task applies **at its waypoint**. It is not a permanent setting.

Once the task is done and the drone moves on to the next point, it must **turn back to face
the direction it is flying** — nose forward, along the current path segment, for the whole
segment. A drone that executes `yaw90` and then keeps that heading while flying sideways to
the next three waypoints has not implemented this.

So the heading logic is:

| Situation | Required heading |
|---|---|
| Flying between points (the normal case) | Along the direction of travel |
| At a waypoint with a `yaw` task | The commanded angle, held until the task completes |
| At a waypoint with `takeoff` / `land` / `landtakeoff` | Whatever you had; do not spin during the manoeuvre |

The direction of travel for a segment from **p** to **q** is
`atan2(q.y - p.y, q.x - p.x)` in ENU. Turn to it before you start the segment rather than
midway through it, and **unwrap the angle** — `atan2` jumps between `+π` and `-π`, and a yaw
setpoint that jumps by `2π` makes the drone spin a full turn the wrong way.

This is the same mechanism you need in [E1.3](03_outdoor_gps_mission.md) for tangent heading on
the figure-8. Write it once, in a form you can reuse.

## Acceptance criteria for the whole sub-exam

- The mission runs **end to end, unattended**, from `ros2 run` to disarm after landing.
- The drone does not collide with the hangar — **including the shelving racks**, which are
  solid despite their see-through visual mesh (see [E1.1 §2](01_map_and_path_planning.md)).
- All tasks in the mission file are executed, in order.
- Between waypoints the drone faces the direction it is flying, and it does not stop at every
  intermediate point of the planned path.
- It works with a **mission file supplied at the defence**.

## Hints

- **Fly it by hand from the terminal first.** Arm, take off, push one setpoint — the
  `ros2 service call` / `ros2 topic pub` commands are in
  [`useful_links.md`](useful_links.md#2-commands-you-will-use-constantly). Once that works, the
  node is mostly the same calls in a loop.
- `type_mask` in `mavros_msgs/msg/PositionTarget` decides which fields are used. Getting it
  wrong means the drone ignores your yaw, or your position, and it fails silently. Run
  `ros2 interface show mavros_msgs/msg/PositionTarget` and read the constants.
- Position setpoints in ArduPilot's `GUIDED` mode are latched — the vehicle keeps flying to
  the last one. **Velocity and attitude targets are not**: they expire after `GUID_TIMEOUT`
  (3 s by default) and the vehicle stops. Relevant if you use velocity control.
- If nothing arms, read the SITL console. ArduPilot tells you exactly why it refuses
  (pre-arm checks, EKF not ready, bad frame class). It is never a mystery.
- Log your state transitions with timestamps. It makes the defence much easier for you.

## Deliverables

- ROS 2 package building with `colcon build`.
- Instructions for running the mission with an arbitrary mission file.
- Rosbag or screen recording of a complete successful mission.

## Links

- [MAVROS plugin list — every topic and service, with types](http://wiki.ros.org/mavros/Plugins)
- [MAVLink `SET_POSITION_TARGET_LOCAL_NED`](https://mavlink.io/en/messages/common.html#SET_POSITION_TARGET_LOCAL_NED)
- [MAVLink `POSITION_TARGET_TYPEMASK`](https://mavlink.io/en/messages/common.html#POSITION_TARGET_TYPEMASK)
- [ArduPilot — copter commands in GUIDED mode](https://ardupilot.org/dev/docs/copter-commands-in-guided-mode.html)
- [ROS 2 cheat sheet](../../tutorial/ros2_cheatsheet.md) — workspace, console commands, topics in C++
- [`mt_executor_demo`](../../mt_executor_demo/README.md) — the worked node example
- Everything else: [`useful_links.md`](useful_links.md)
