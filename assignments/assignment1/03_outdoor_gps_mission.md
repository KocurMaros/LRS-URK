# A1.3 — Outdoor mission: GPS, compass and continuous trajectories (7 points)

Everything so far ran indoors, where the simulator hands you a clean local position. Outdoors
you have **GPS** and a **magnetic compass** instead, and this is the part of Assignment 1 that also
runs on the **real drone** — so it has to survive real sensors: noise, a compass that is not
aligned with your local X axis, and an origin that moves every time you power the vehicle.

> **The world.** The outdoor mission is flown in the open-field world
> `worlds/fei_lrs_outdoor.world` *(added to this repository — check `worlds/` and pull before
> you start; if it is not there yet, ask your teacher)*. Any open `gz sim` world with a working
> NavSat/GPS sensor will do for development — for example the `iris_runway` world shipped with
> [`ardupilot_gazebo`](https://github.com/ArduPilot/ardupilot_gazebo).

## The mission

```
        ┌────────── waypoint square, side S = 5 m, at 5 m altitude ──────────┐
        │  W1 ──────────────────────► W2                                     │
        │   ▲              ╲          │        yaw always pointing           │
        │   │               ╲  POI    │        at the POI                    │
        │   │                ★        ▼                                      │
        │  W4 ◄────────────────────── W3                                     │
        └────────────────────────────────────────────────────────────────────┘
                              then, centred on the POI:

                              figure-8  ∞   x(t) = A·sin(t)      A = 3 m
                                            y(t) = A·sin(t)·cos(t)
                              yaw = tangent to the path
```

1. **Take off** to **5 m** above the launch point and stabilise.
2. **Fly the waypoint square** — four corners, in order — while the drone's **yaw stays locked
   on a fixed point of interest (POI)** on the ground at the centre of the square. The drone
   translates sideways and backwards; its nose keeps pointing at the POI the whole time.
3. **Fly a figure-8** centred on the POI, as a **continuous trajectory** — a ROS 2 timer
   publishing a fresh setpoint every cycle from the parametric equations, *not* a list of
   waypoints.
4. **Align the heading with the trajectory tangent** during the figure-8 — nose forward,
   along the direction of travel.
5. **Return to launch and land.**

POI position and the traversal rate are **your parameters** — declare them as ROS parameters
and justify your values. The geometry is fixed:

| Parameter | Value |
|---|---|
| Flight altitude | **5 m** above the launch point |
| Square side `S` | **5 m** |
| Figure-8 amplitude `A` | **3 m** |

These are deliberately small: the whole mission fits in a box roughly 6 × 5 m, which is what
makes it safe to fly on the real drone on a normal field. Keep them — do not scale the mission
up because it looks better in simulation.

## Specification

### 1. GPS and compass handling — 1.5 points

This is the foundation for everything else in this sub-assignment.

- **Subscribe to the GPS fix** (`/mavros/global_position/global`, `sensor_msgs/msg/NavSatFix`)
  and **wait for a usable fix before arming.** Check the fix status and the satellite count —
  do not take off on a fix that has not converged. Indoors this never fails; outdoors it does.
- **Establish the origin.** Capture the **home position**
  (`/mavros/home_position/home`, `mavros_msgs/msg/HomePosition`) or the first valid fix, and
  define your mission relative to it. The real drone's home is a different lat/lon every
  session — nothing in your mission may contain a hardcoded absolute coordinate.
- **Convert between geodetic and local coordinates.** Define the POI and the square corners
  in **latitude/longitude** and convert them to local ENU metres (or drive them directly as
  global setpoints via `/mavros/setpoint_raw/global`,
  `mavros_msgs/msg/GlobalPositionTarget`). Both directions must work; you need geodetic → local
  for planning and local → geodetic for reporting where you actually flew.
  You can use [GeographicLib](https://geographiclib.sourceforge.io/) or implement the local
  tangent-plane approximation yourself — over a 50 m field a flat-Earth approximation is fine,
  **if you say so in the documentation and state its error.**
- **Use the compass.** Read `/mavros/global_position/compass_hdg` (`std_msgs/msg/Float64`,
  degrees, 0 = magnetic North, increasing **clockwise**) and reconcile it with the yaw you get
  from `/mavros/local_position/pose`, which is in **ENU** (0 = East, increasing
  **counter-clockwise**). The relation is:

  ```
  yaw_ENU_deg = 90 - heading_deg      (wrapped into (-180, 180])
  ```

  Verify this empirically — print both while you rotate the drone in the simulator. Your
  documentation must state which convention each of your angles is in. Every heading bug in
  this assignment comes from skipping this step.
- **Be clear about altitude.** AMSL (`NavSatFix.altitude`), relative to home
  (`/mavros/global_position/rel_alt`), and your local Z are three different numbers. "5 m"
  means **5 m above the launch point**. Say which one you command and which one you check.

**Accepted when:** you can print, at any moment, the drone's position as lat/lon/alt **and**
as local ENU metres from home, plus its heading in both conventions — and the numbers agree
with what the simulator shows.

### 2. Takeoff to 5 m — 0.5 points

Arm, take off to **5 m above launch**, hold position and altitude stably before continuing.
Confirm the altitude has actually been reached rather than sleeping for a fixed time.

### 3. POI tracking around the waypoint square — 1.5 points

Fly the four corners of the square in order, with **yaw continuously pointing at the POI**.

- The POI is a **static ground coordinate** at the centre of the square, given as lat/lon (or
  as a local offset from home) — a parameter, not a constant in the code.
- Yaw is **recomputed continuously**, not once per corner. Between corners the required
  heading changes constantly; a drone that snaps to the right heading only at the corners does
  not score full points here.
- The drone will therefore fly **sideways and backwards**. That is the point of the exercise.
- Remember the POI is on the **ground** and you are at 5 m: decide whether you are aiming the
  yaw (horizontal bearing only) or a gimbal/camera pitch too. Yaw is what is required; say what
  you did. Note that at 5 m altitude and only 3.5 m of horizontal distance from the corners,
  the drone is looking steeply downward — the bearing changes fast, which is precisely what
  makes continuous recomputation necessary.

**Accepted when:** across the whole square the angular error between the drone's nose and the
bearing to the POI stays small (a few degrees), verifiable from your rosbag.

### 4. Figure-8 as a continuous trajectory — 2.0 points

This is the core of the sub-assignment. **No discrete waypoints.** Write a ROS 2 timer callback that,
on every tick, evaluates the parametric equations at the current time and publishes a fresh
setpoint:

$$x(t) = A \sin(t)$$

$$y(t) = A \sin(t) \cos(t)$$

with the curve **centred on the POI** and flown at constant altitude.

Requirements:

- A **`rclcpp` / `rclpy` timer** at a steady rate (20–50 Hz is a good range) computing
  `t = ω · (now − t_start)` and publishing to `/mavros/setpoint_raw/local` (or
  `/mavros/setpoint_position/local`).
- The **rate parameter `ω`** must exist and be tunable, so you can slow the figure down.
- The drone completes **at least one full lap** (`t` from `0` to `2π`) and the flown track
  visibly matches the shape.
- Handle the transition **into** the trajectory: at `t = 0` the curve is at the POI centre, so
  fly there before starting the timer. Starting the timer while the drone is still at a square
  corner produces a violent lunge toward the centre — on the real drone that is how you break
  something.

Geometry, so you can size it: the curve spans `2A` in x and `A` in y (from `-A/2` to `+A/2`),
and it crosses itself at the centre. With `A = 3 m` that is a **6 × 3 m** figure — it fits
inside the waypoint square.

The speed is `|v| = A·ω·sqrt(cos²t + cos²2t)`, largest at the crossing point where it equals
`A·ω·√2`. So for `A = 3 m` and a 1.5 m/s speed limit:

```
ω ≤ 1.5 / (3·√2) ≈ 0.35 rad/s   →   lap time = 2π/ω ≈ 18 s
```

Start there. Put the calculation for whatever `ω` you actually use in the documentation, and
check the result against the geofence before you fly it for real.

### 5. Tangent heading alignment — 1.0 point

During the figure-8 the nose must point **along the direction of travel**:

```
yaw(t) = atan2( ẏ(t), ẋ(t) )        with   ẋ = A·cos(t),   ẏ = A·cos(2t)
```

- Publish the yaw together with each position setpoint (`type_mask` must not ignore yaw).
- Alternatively use `yaw_rate` — analytically or by differentiating. Either is accepted;
  explain which and why.
- **Watch the wrap-around.** `atan2` jumps between `+π` and `-π`. A yaw setpoint that jumps by
  `2π` makes the drone spin a full turn in the wrong direction. Unwrap it.
- Note that at the crossing point the curve passes through itself in two different directions —
  the heading is genuinely different on the two passes, and that is correct.

**Accepted when:** the nose follows the path smoothly through a full lap, with no spins and no
snap-backs.

### 6. Return to launch, land, and abort handling — 0.5 points

- After the figure-8, return to the launch point and **land safely**.
- Implement an **abort path**: a way to stop the mission cleanly and bring the vehicle to a
  safe state (hold, RTL, or land) — from a service call, a topic, or a keypress. On the real
  drone this must exist before you fly.
- Your node must behave sensibly if MAVROS drops out or the mode is changed from the RC
  transmitter — at minimum, notice it and stop sending setpoints. Do not fight the safety pilot.

## Doing this on the real drone

From week 4 you may fly this mission outdoors on the real UAV, once the conditions in
[`../README.md`](../README.md#flying-the-real-drone) are met — fully submitted Assignment 1,
a passed consultation, and the safety briefing.

**A teacher is always present and a safety pilot always holds an RC transmitter that can take
over instantly. Never power a real vehicle without a teacher present.**

### Pre-flight checklist

Before your code goes anywhere near a real vehicle:

- [ ] The complete mission flies in simulation, unattended, twice in a row.
- [ ] **No hardcoded absolute coordinates.** Everything is relative to the home position
      captured at startup.
- [ ] The node **waits for a good GPS fix** and refuses to arm without one.
- [ ] **Geofence:** your mission's maximum distance from home and maximum altitude are computed,
      written down, and inside the limits set on the vehicle. With `S = 5 m` and `A = 3 m` the
      mission stays within ~3.5 m of the POI horizontally and 5 m vertically — know where the
      POI is relative to home, and add the two.
- [ ] The **abort path works** and you have demonstrated it in simulation.
- [ ] Altitudes are **relative to home**, and you know which topic you are checking.
- [ ] The compass convention is verified, not assumed — with a real compass, a sign error
      points the drone the other way.
- [ ] Battery, failsafes and RTL are configured; you know what the vehicle does on link loss.
- [ ] You know the **wind limit** and today's conditions. A drone flying a 6 × 3 m figure-8 at
      1.5 m/s in 8 m/s wind is not doing what your maths thinks it is.

## Hints

- **The simulator lies to you in a useful way.** SITL's GPS is nearly perfect. Before flying
  for real, add noise or lower the SITL GPS accuracy and check your code still behaves.
- Print your computed setpoint alongside the reported position every cycle. If the drone flies
  a mirrored figure-8, you have an ENU/NED problem, not a maths problem.
- Publish your intended trajectory as an RViz `Path` or `MarkerArray` and record the actual
  one. Overlaying the two is the fastest way to show your work at the defence — and it makes a
  good figure for the documentation.
- Start with the figure-8 at **low speed** — halve `ω` until the shape is right, then work back
  up. Correctness first, speed later.
- `ros2 bag record -a` before every run. It costs nothing and saves the demo.

## Deliverables

- The outdoor mission as part of your ROS 2 package, launchable separately from the indoor one.
- Parameters (POI, square side, amplitude, rate, altitude) exposed and documented.
- Rosbag of a complete successful outdoor mission in simulation.
- A plot or screenshot of the flown track versus the commanded trajectory.

## Links

- [MAVROS plugin list — topics, services and their types](http://wiki.ros.org/mavros/Plugins)
- [MAVLink `SET_POSITION_TARGET_GLOBAL_INT`](https://mavlink.io/en/messages/common.html#SET_POSITION_TARGET_GLOBAL_INT)
- [MAVLink `POSITION_TARGET_TYPEMASK`](https://mavlink.io/en/messages/common.html#POSITION_TARGET_TYPEMASK)
- [ArduPilot — GUIDED mode](https://ardupilot.org/copter/docs/ac2_guidedmode.html)
- [ArduPilot — compass calibration](https://ardupilot.org/copter/docs/common-compass-calibration-in-mission-planner.html)
- [ArduPilot — failsafes](https://ardupilot.org/copter/docs/failsafe-landing-page.html)
- [GeographicLib](https://geographiclib.sourceforge.io/) — geodetic ↔ local conversions
- [Lemniscate of Gerono](https://en.wikipedia.org/wiki/Lemniscate_of_Gerono) — the curve you are flying
- [ROS 2 cheat sheet](../../tutorial/ros2_cheatsheet.md) — timers, publishers, topics in C++
- Everything else: [`useful_links.md`](useful_links.md)
