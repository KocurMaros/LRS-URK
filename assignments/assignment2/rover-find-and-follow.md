# Find-and-follow a moving rover

A fourth Assignment 2 option alongside the topics in [`README.md`](README.md): each drone finds,
then follows, its own moving rover using only its down camera — never a known coordinate. Like
the other topics, this extends the control node you already wrote for
[Assignment 1](../assignment1/README.md) (`MavrosClient`, `SetpointStream`, `PositionController`,
`HeadingPolicy`, the `MultiThreadedExecutor` + callback-group pattern) — reuse it, don't
reinvent it. Confirm with your exercise teacher before committing to this topic; the rules
shared by all Assignment 2 topics (threshold, documentation, git hygiene) in
[`README.md`](README.md) apply here too.

## What already exists — read it before writing any code

`scripts/generate_precision_landing.py` generates `worlds/fei_lrs_precision_landing.world` from
`worlds/fei_lrs_outdoor.world`. Running it also writes
`models/aruco_rover_<N>/{model.sdf,model.config,materials/textures/aruco_<N>.png}`. Re-run it
after any edit to the templates in that script — the world file itself is marked
"GENERATED ... do not edit by hand."

The generated world has, right now:

- **Two independent drone/rover pairs**, not one:
  - `drone_1` / `aruco_rover_1`, ArUco marker id **1**, ArduPilot SITL instance **0**,
    `fdm_port_in` **9002**, `SYSID_THISMAV` **1**, spawned at `(-10, -10)`.
  - `drone_2` / `aruco_rover_2`, marker id **2**, instance **1**, `fdm_port_in` **9012**,
    `SYSID_THISMAV` **2**, spawned at `(10, -10)`.
  - The pairing rule is **marker id == the drone's own `SYSID_THISMAV`**. Keep that rule; it is
    how a drone knows which rover is *its* rover when more than one marker might be visible.
- **One down-facing (nadir) camera per drone**, replacing the outdoor world's stereo pair.
  Gazebo topic `drone_<N>/down_camera/image_raw`, 640x480, 60 deg horizontal FOV, 30 Hz. Its
  mount pose is **not** simply "pointing straight down along the drone's -Z" by inspection —
  work out the actual optical-frame convention from `down_camera_xml()` and the link pose
  override in `build_drone()` in `scripts/generate_precision_landing.py`, and verify it
  empirically (log a detection's estimated pose against a known ground-truth position) before
  trusting any sign or axis in your pose math. This is exactly the kind of mistake
  [`03_outdoor_gps_mission.md`](../assignment1/03_outdoor_gps_mission.md)'s ENU/NED warnings are
  about.
- **Each rover** carries a 1.00 m white pad with a marker (`DICT_4X4_50`) on top. Read
  `scripts/generate_precision_landing.py`'s own `PAD_SIZE`/`MARKER_SIZE` constants and
  `generate_marker_png()` carefully before deciding what physical size to hand your pose
  estimator — the size the plate is generated at and the size `cv2.aruco`'s detector actually
  reports corners for are not automatically the same thing once a texture has a quiet-zone
  margin baked into it, and using the wrong one silently scales every distance you compute. This
  is exactly the sort of thing "verify it empirically" above is for.
- **Rover motion, currently**: a fixed circle, driven by `gz-sim-velocity-control-system`'s
  static `<initial_linear>`/`<initial_angular>`. This must change — see "Randomize the rover
  motion" below.
- **Ground-truth rover odometry** is published on `model/aruco_rover_<N>/odometry`. That topic
  exists for your own debugging/validation, not for the follow controller to consume — the
  point of this exercise is closed-loop visual tracking from the camera, and a solution that
  quietly reads this topic instead has not done that.
- **Nothing to run any of this in ROS 2 exists yet.** You are building the bring-up scripts and
  bridge launch file, not finding a bug in ones that are already there.
- `check_clearance()` in the generator script already validates that rover circles and drone
  spawn points stay clear of the world's trees/bushes by at least 5 m. Keep whatever you change
  passing that check (or extend it) — a rover that can drive into scenery will, and so can a
  drone that searches too wide an area at too low an altitude (the trees have real canopy height
  and radius; check both before picking a search pattern's extent).

## The objective

1. Each drone (both, independently — this should work with two SITL/MAVROS stacks running at
   once) arms, takes off, and climbs to a safe search altitude.
2. It **searches** for its own rover using the down camera — detect ArUco markers in the image,
   read off the id, and confirm it matches this drone's `SYSID_THISMAV` before treating it as
   the target. A marker with the wrong id (the *other* rover's) must be ignored, not chased.
   Do not assume the rover's position is known in advance; this has to be a real detect, not a
   fly-to-a-known-coordinate.
3. Once confirmed, switch to **tracking**: hold a fixed altitude *above* the rover — a
   configurable parameter, not a hardcoded number — and continuously reposition to stay above
   it as it moves. **Never land.** There is no landing state in this exercise.
4. If the marker is lost from view for longer than a short, configurable timeout, drop back into
   a search behaviour instead of continuing to fly toward a stale last-known position.

## Randomize the rover motion

A perfect circle is a solved problem — a controller could precompute it and never actually
react to anything. Replace it with randomly changing speed and direction:

- `gz-sim-velocity-control-system` can take a live Twist command on a topic instead of only a
  static `initial_linear`/`initial_angular` — check the Gazebo Harmonic docs for the plugin's
  `<topic>` option and the exact message type, don't assume; confirm it empirically against a
  running world (`gz topic -l` and friends) the same way you're being asked to confirm the
  camera pose above. Bridge that topic with `ros_gz_bridge` the same way you'll bridge the
  cameras.
- Write a small node (Python is fine) that, per rover, publishes a new random forward speed and
  yaw rate every few seconds. Keep the speed in the same order of magnitude as the fixed
  circle's current speed — this is a small field, not a racetrack — and keep whatever bounds you
  pick consistent with `check_clearance()`'s 5 m margins.
- Decide, and document, whether you still need the static `initial_linear`/`initial_angular` in
  `models/aruco_rover_<N>/model.sdf` as a starting value or whether your randomizer node should
  own motion from t=0. Either is fine; be explicit about which.

## All the instruments you'll need

- **`ros_gz_bridge`** (or an equivalent `ros_gz` bridge config) for: both cameras'
  `image_raw` topics, their matching `camera_info` topics (gz-sim's camera sensor publishes one
  automatically — get the exact topic name from `gz topic -l` on the running world, don't guess
  it), and the rover velocity-command topic(s) from the randomizer above.
- **OpenCV's `cv2.aruco`**, `DICT_4X4_50` (matching `scripts/generate_precision_landing.py`), for
  detection and pose estimation, plus **`cv_bridge`** to get from `sensor_msgs/msg/Image` to an
  OpenCV `Mat`. Check what pose-estimation API is actually available in the installed OpenCV
  version before writing to it — the old `estimatePoseSingleMarkers` path is deprecated/removed
  in newer OpenCV and replaced with a `solvePnP`-based approach; `generate_precision_landing.py`
  already has to branch on OpenCV version for marker generation, so expect the same here.
- **Two independent SITL instances and two independent MAVROS instances**, one pair per drone,
  each in its own namespace, each pointed at its own vehicle. The single-vehicle
  `scripts/run_sitl.sh`/`scripts/run_mavros.sh` pattern only stands up one of each — you need a
  multi-instance equivalent (matching `fdm_port_in` 9002/instance 0 and 9012/instance 1, and
  each vehicle's own home location) and a multi-MAVROS launch or a parametrized
  `run_mavros.sh`-style script per vehicle. Port collisions between the two MAVROS instances
  (the 14550-family ports) are the classic way this half-works — pick and document distinct
  ports per vehicle, and check whichever MAVROS namespace convention your installed MAVROS
  version actually expects (verify with `ros2 topic info <topic> --verbose` that a topic you
  expect to be publishing actually has a publisher — don't assume a namespace argument does what
  you think it does).
- **`gz sim` running `worlds/fei_lrs_precision_landing.world`**, with `GZ_SIM_RESOURCE_PATH`
  including `models/` — same convention `scripts/run_gazebo.sh` already uses for the other
  worlds.
- **Your own Assignment 1 control-node architecture — reuse it, don't reinvent it.** The
  `MultiThreadedExecutor` with separate callback groups for telemetry, the mission-tick state
  machine, the setpoint publisher, and services; `MavrosClient` for MAVROS I/O; `SetpointStream`
  for a steady-rate position+yaw publisher; `PositionController` for arrival logic — all of it
  is yours already. Say clearly in your documentation if you decide a new package is actually
  warranted instead of extending your existing one, and why.

## State machine

Adapt the state machine shape you already have, don't invent a fresh one:

```
INIT -> WAIT_FOR_FCU -> WAIT_FOR_TELEMETRY -> SET_GUIDED -> ARM -> TAKEOFF -> SEARCH -> TRACKING
```

with `TRACKING -> SEARCH` on a detection timeout, and an abort path (service or topic, matching
whatever `~/abort` convention you already used in Assignment 1) that brings the vehicle to a
safe hold/RTL — there is no `LAND` state to reach in normal operation.

## Deliverables

- Multi-instance SITL/MAVROS bring-up scripts.
- A bridge launch file for both cameras' image + camera_info topics and the rover
  velocity-command topic(s).
- The ArUco detector + follow controller (one node handling both drones by namespace, or two —
  your call, document which and why), built on your existing node architecture.
- The rover-motion randomizer, and whatever edits to `scripts/generate_precision_landing.py` /
  `models/aruco_rover_*/model.sdf` it needs — regenerate the world after editing the generator,
  never hand-edit the generated `.world`/`.sdf` files directly.
- A short doc explaining how to bring all of this up from a clean checkout: the world, both SITL
  instances, both MAVROS instances, the bridge, the randomizer, and both follow nodes — in
  order, with the actual commands.
- State explicitly, in that doc: how you go from a single camera detection to a world-frame
  target position (camera intrinsics, marker size, the camera's extrinsic offset from the drone
  body you worked out above), your altitude-above-rover parameter and its default, your
  detection-timeout value and what "lost" triggers, and any known limitations.

## Standards this repo already holds everything else to — apply them here too

- Every tunable (altitudes, timeouts, follow distance, randomizer speed bounds) is a declared,
  documented ROS parameter, not a number buried in code.
- State transitions are logged.
- There is a working abort path, demonstrated, not just written.
- **Verify by actually running it in `gz sim` and watching both drones find and follow their
  rovers, including through a rover-lost/found cycle** — do not report this done from reading
  the code. If something doesn't work, say so plainly along with what you think the cause is,
  the same standard [`04_documentation_and_defence.md`](../assignment1/04_documentation_and_defence.md)
  sets for the rest of your submission.

## Tips and tricks

- **The rover model's wheels are cosmetic** — motion comes entirely from
  `gz-sim-velocity-control-system` applying a body-frame twist, not from the wheel joints.
  A four-wheeled platform with a single box collision and no rolling resistance is not
  automatically stable at all speed/yaw-rate combinations; if you see a rover tip onto its side
  after running for a while (its marker then stops facing the camera at all, from any
  altitude — check the rover's own `orientation` on `model/aruco_rover_<N>/odometry` if a drone
  that flies right over its rover's last-known area never detects anything), that is a
  known characteristic of this rover model, not a bug in your detector. Keep your randomizer's
  speed/yaw-rate bounds modest and note the behaviour in your documentation if you hit it,
  rather than chasing it as if it were your own code.
- **Sim time vs. wall-clock time.** `ros_gz_bridge` topics carry Gazebo's own simulation-clock
  timestamps; MAVROS's do not unless you also bridge `/clock` and run every node with
  `use_sim_time`. Comparing the two directly (e.g. to time-match a camera frame against a pose
  reading) will not do what you expect unless you either bridge the clock properly or design
  around not needing to compare them.
- **A fast search leg plus a slow vision pipeline is a bias, not just noise.** If your follow
  node reads "current" telemetry at the moment it finishes processing a frame rather than at the
  moment the frame was captured, and the drone is moving quickly, the position you compute for
  a detection will be off by roughly (vehicle speed) x (pipeline latency) — consistently in the
  direction of travel, not a random scatter. Capping your search/track speed is a simpler fix
  than trying to time-synchronise two topics that may not even share a clock (see above).
- **MAVProxy needs a real, interactive terminal.** If you ever script SITL bring-up for
  automated testing rather than running it by hand in a terminal, a backgrounded MAVProxy
  process with no controlling TTY will exit almost immediately (it reads commands from stdin)
  — this looks exactly like "SITL never sends a heartbeat" and is not.
