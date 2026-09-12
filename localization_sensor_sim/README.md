# Localisation sensor simulator

This ROS 2 package supplies the imperfect sensor data used by the
[Assignment 2 drone-localisation task](../assignments/assignment2/localization.md). It is teaching
infrastructure, not a reference solution: students receive noisy GPS, drifting visual odometry
(VO), and a biased yaw-rate gyro, then implement their own eight-state Kalman filter and use its
estimate for flight control.

The package is compatible with ROS 2 Humble and Jazzy and is intended for Gazebo Harmonic. The
implementation uses `rclpy` and NumPy and deliberately avoids APIs specific to only one of those
ROS distributions.

## Why this package exists

MAVROS and Gazebo expose localisation outputs that are too accurate or too complete for this
assignment. Letting students subscribe to those outputs would bypass the estimation problem.
This package creates a small, controlled sensor suite with repeatable failure cases:

- GPS provides an absolute but noisy position at a low rate.
- VO provides a smooth, higher-rate track that gradually drifts.
- IMU provides only yaw rate, including noise and a hidden static bias.
- Ground truth is retained on a clearly separated evaluation topic for teachers and plots.
- Services let the teacher create outages and a GPS outlier during a defence.

The result is complicated enough to require covariance propagation, asynchronous updates,
gyro-bias estimation, yaw wrapping, and innovation gating, without turning the assignment into a
full inertial-navigation project.

## System overview

```text
Gazebo localisation world
  |
  +-- /evaluation/ground_truth_gz --[ros_gz_bridge]-->
  |      /localization/_ground_truth_raw
  |
  +-- /localization/imu_gz -------[ros_gz_bridge]-->
  |      /localization/_imu_raw
  |
  +-- /clock ----------------------[ros_gz_bridge]--> /clock
                                                      |
                                                      v
                                         sensor_simulator node
                                           |   |   |   |
                                           |   |   |   +--> evaluation truth
                                           |   |   +------> sanitised IMU
                                           |   +----------> drifting VO
                                           +--------------> noisy GPS
```

The two topics whose names begin with `/localization/_` are internal bridge inputs. Students must
not use them. The node transforms ground truth into the course ENU convention, applies seeded
corruption, and publishes the public sensor contract.

## Files

| File | Purpose |
|---|---|
| `localization_sensor_sim/sensor_simulator.py` | ROS publishers, subscriptions, services, message covariances, timestamp scheduling, and reset handling |
| `localization_sensor_sim/sensor_model.py` | Coordinate transforms and the deterministic GPS/VO corruption model |
| `config/sensors.yaml` | Public rates, noise, drift, covariance-related values, outage durations, and ROS corruption seed |
| `launch/localization_sensors.launch.py` | Starts the Gazebo-to-ROS bridges and simulator node |
| `test/` | Tests transforms, rates, drift, outliers, determinism, reset behaviour, and configuration |
| `../worlds/fei_lrs_gazebo_localization.world` | Dedicated world containing the 100 Hz biased IMU and 3D truth publisher |

## Starting the complete pipeline

Run all commands from the repository root. Gazebo is started separately because the same seed
must be visible and easy to change during assessment.

### 1. Start the dedicated world

```bash
GZ_SIM_RESOURCE_PATH="$PWD/models:${GZ_SIM_RESOURCE_PATH:-}" \
  gz sim -r -v 4 --seed 42 "$PWD/worlds/fei_lrs_gazebo_localization.world"
```

The existing `scripts/run_gazebo.sh` is intentionally not changed. Keeping the seeded command
explicit also prevents this assignment's world from becoming the default for other exercises.

### 2. Start SITL and MAVROS

```bash
# Separate terminals
scripts/run_sitl.sh
scripts/run_mavros.sh
```

### 3. Build and launch the sensor package

```bash
colcon build --packages-select localization_sensor_sim
source install/setup.bash
ros2 launch localization_sensor_sim localization_sensors.launch.py seed:=42
```

Use the same numeric seed for Gazebo and the ROS launch. Gazebo uses it for the physical IMU
noise and hidden bias; the ROS node uses it for GPS and VO corruption. The two simulators have
separate random-number generators, so “same seed” means a repeatable complete scenario, not that
they generate identical random sequences.

An alternative parameter file can be supplied without editing the default:

```bash
ros2 launch localization_sensor_sim localization_sensors.launch.py \
  seed:=73 params_file:=/absolute/path/to/teacher_sensors.yaml
```

## Public ROS interface

### Topics

All output timestamps come from simulation messages, not wall-clock arrival time.

| Topic | Type | Simulation-time rate | Intended use |
|---|---|---:|---|
| `/localization/gps` | `geometry_msgs/msg/PoseWithCovarianceStamped` | 5 Hz | Student estimator input: absolute ENU position |
| `/localization/vo` | `nav_msgs/msg/Odometry` | 30 Hz | Student estimator input: drifting pose/yaw and body-frame linear velocity |
| `/localization/imu` | `sensor_msgs/msg/Imu` | 100 Hz | Student estimator input: `angular_velocity.z` only |
| `/evaluation/ground_truth` | `nav_msgs/msg/Odometry` | 100 Hz | Teacher evaluation or an isolated plotting process |

The publishers use sensor-data QoS. Student subscribers should therefore use
`rclcpp::SensorDataQoS()` in C++ or `qos_profile_sensor_data` in Python.

The IMU message is sanitised before publication:

- `orientation_covariance[0]` is `-1`, marking orientation unavailable;
- `linear_acceleration_covariance[0]` is `-1`, marking acceleration unavailable;
- angular X and Y are zero with very large covariance;
- only angular Z and its configured variance are valid.

This prevents accidental use of orientation or acceleration even if a bridge version fills those
fields differently.

### Teacher services

| Service | Type | Effect |
|---|---|---|
| `/localization/set_gps_enabled` | `std_srvs/srv/SetBool` | Starts or stops GPS publication |
| `/localization/set_vo_enabled` | `std_srvs/srv/SetBool` | Starts or stops VO publication |
| `/localization/inject_gps_outlier` | `std_srvs/srv/Trigger` | Adds a large innovation to the next enabled GPS sample |

Typical defence sequence:

```bash
# Fifteen-second GPS outage during a middle mission leg
ros2 service call /localization/set_gps_enabled \
  std_srvs/srv/SetBool "{data: false}"
sleep 15
ros2 service call /localization/set_gps_enabled \
  std_srvs/srv/SetBool "{data: true}"

# Short VO tracking loss
ros2 service call /localization/set_vo_enabled \
  std_srvs/srv/SetBool "{data: false}"
sleep 3
ros2 service call /localization/set_vo_enabled \
  std_srvs/srv/SetBool "{data: true}"

# The next GPS sample should be rejected by the student's innovation gate
ros2 service call /localization/inject_gps_outlier \
  std_srvs/srv/Trigger "{}"
```

During an outage, corruption state continues evolving but the selected measurements are not
published. Restoring a sensor therefore does not restart or reseed it, which gives students a
realistic recovery case. The outlier request remains pending if GPS is disabled and is applied to
the first GPS sample after it is enabled again.

## Frames and coordinate conversion

Gazebo spawns the drone at world position `(13, 7, 0)` with yaw `0`. The course and MAVROS use a
rotated ENU convention, so the simulator applies:

```text
x_ENU = -y_Gazebo
y_ENU =  x_Gazebo
z_ENU =  z_Gazebo
yaw_ENU = wrap(yaw_Gazebo + pi/2)
```

The expected initial transformed pose is consequently close to `(-7, 13, 0)` with yaw `pi/2`.
The full truth quaternion is rotated as well, so roll and pitch remain available to the teacher's
3D evaluator. The student filter is only required to estimate yaw.

Frame contract:

- GPS uses `map`.
- Evaluation truth uses `map` with child frame `base_link`.
- VO pose uses `vo_odom` with child frame `base_link`.
- VO linear twist is expressed in `base_link`, not in ENU.
- IMU uses `base_link`.

The VO frame starts aligned with the transformed true pose, then develops its own drift. Students
must not assume that `vo_odom` remains identical to `map`.

## How corruption is generated

### GPS

At each scheduled sample, independent Gaussian position noise is added using the configured XYZ
standard deviations. The default is `(0.6, 0.6, 0.9)` metres. Position covariance is published as
the square of those values, while orientation covariance is set very large because GPS orientation
is not an observation.

The outlier service adds a seeded random-direction offset with a configured magnitude. The final
offset is guaranteed to be at least `gps_outlier_min_m`, so it remains an unambiguous gating test
even when ordinary GPS noise points in the opposite direction.

### Visual odometry

VO is maintained as a continuous drifting track rather than independently perturbing every true
pose. True motion increments are converted to the body frame, then corrupted by:

- one seeded scale error;
- a seeded velocity bias;
- velocity-bias random walk;
- position-step noise;
- yaw-rate bias and random walk;
- small pose/yaw and body-velocity output noise.

The corrupted increments are integrated in the VO track frame. This produces the expected
short-term smoothness and long-term drift. The reported linear twist is body-frame velocity so
students must either use an EKF measurement model or rotate it using their current yaw estimate.

### IMU

The dedicated Gazebo IMU is mounted directly on `drone_body` and publishes at 100 Hz. Its Z gyro
has Gaussian noise plus a seeded static bias centred around magnitude `0.02 rad/s`; Gazebo may
choose either bias sign. It is separate from
`fei_lrs_drone/imu_link::imu_sensor`, which remains the IMU selected by the ArduPilot plugin.
Therefore this assignment sensor cannot corrupt ArduPilot's own flight dynamics input.

## Simulation-time reset behaviour

GPS and VO are scheduled from incoming truth timestamps. This matters when Gazebo runs slower
than real time: `ros2 topic hz` measures wall-time arrivals and may display lower rates, while the
header stamps still show 5, 30, and 100 Hz in simulation time.

If an incoming timestamp moves backwards, for example after a Gazebo world reset, the node:

1. clears the VO track and publication deadlines;
2. resets the GPS/VO random-number generator to the configured seed;
3. clears any pending outlier request;
4. initialises again from the first truth sample after the reset.

This makes repeated runs with the same seeds reproducible and prevents a negative time step from
creating invalid drift or velocity.

## Parameters teachers are expected to change

The defaults in `config/sensors.yaml` are public. This is intentional: students should design
against stated sensor characteristics while remaining robust to a different random trace.

Useful groups are:

- `random_seed` — GPS/VO seed, normally overridden by the launch argument;
- `gps_rate_hz`, `gps_position_stddev`, and `gps_outlier_*`;
- `vo_rate_hz`, scale/bias/random-walk settings, and pose/velocity noise;
- `imu_yaw_rate_variance` — covariance attached to the sanitised Z gyro;
- `required_gps_outage_s` and `suggested_vo_outage_s` — documented assessment durations.

If the assignment difficulty is changed, prefer creating a teacher YAML override and testing it
before changing the published defaults. Keep the GPS outlier clearly separated from ordinary
noise, and keep VO drift slow enough that it is helpful over a GPS outage but visible over a full
mission.

## Student boundaries

The student estimator may consume only:

```text
/localization/gps
/localization/vo
/localization/imu
```

The following are infrastructure or truth and must never reach the estimator/controller:

```text
/evaluation/ground_truth
/localization/_ground_truth_raw
/evaluation/ground_truth_gz
Gazebo world pose topics
MAVROS position, odometry, attitude, heading, or IMU orientation outputs
```

For a defence, `ros2 node info <student_estimator_node>` and a source-code search are the fastest
ways to confirm that no forbidden subscription exists. Ground truth is allowed only in a separate
one-way plotting/evaluation process.

## Verification and maintenance

Build and run the package tests with:

```bash
colcon build --packages-select localization_sensor_sim
source install/setup.bash
colcon test --packages-select localization_sensor_sim
colcon test-result --verbose
```

The tests cover:

- the Gazebo-to-ENU spawn transform and angle wrapping;
- 5 Hz and 30 Hz simulation-time scheduling from 100 Hz truth;
- deterministic output for equal seeds and changed output for different seeds;
- corruption/RNG reset behaviour;
- configured GPS outlier magnitude;
- finite, drifting VO state;
- public rates, GPS covariance source values, and required outage duration.

Useful live checks:

```bash
ros2 topic list -t
ros2 topic echo /evaluation/ground_truth --once
ros2 topic echo /localization/imu --once
ros2 topic hz /localization/gps
ros2 topic hz /localization/vo
ros2 service list | rg localization
```

After starting SITL and MAVROS, compare `/evaluation/ground_truth` with
`/mavros/local_position/pose`. At rest they should agree near `(-7, 13, 0)` and yaw `pi/2`, apart
from small estimator/startup differences. Quaternions `q` and `-q` represent the same orientation,
so do not compare quaternion components by sign alone.

When changing the world, always confirm that `ArduPilotPlugin/imuName` still names only the
original flight IMU. When changing the bridge, confirm that the public IMU still marks orientation
and acceleration invalid. Existing worlds and launch scripts should remain unchanged; all
assignment-specific behaviour belongs in this package and the dedicated localisation world.

## Troubleshooting

- **No sensor topics:** check that the dedicated localisation world is running, then inspect the
  bridge process output for its three `Creating GZ->ROS Bridge` messages.
- **No callbacks in a student node:** use sensor-data QoS; a reliable subscriber may be
  incompatible with these best-effort publishers.
- **Rates look too low:** compare message header stamps. Wall-time rate falls with Gazebo's
  real-time factor, while simulation-time rate remains configured.
- **Truth starts near `(13, 7)`:** the student is reading raw Gazebo data instead of the transformed
  `/evaluation/ground_truth` topic.
- **An outlier was not visible in `ros2 topic echo --once`:** the injected sample may have been
  published while the short-lived echo subscriber was starting. Start a continuous echo first,
  then call the service.
- **A repeated run differs:** pass the same seed to both `gz sim --seed` and the ROS launch, and
  reset or restart both processes rather than only one of them.
