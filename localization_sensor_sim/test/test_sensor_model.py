"""Tests for seeded localisation sensor corruption."""

import math

import numpy as np

from localization_sensor_sim.sensor_model import (
    SensorCorruptor,
    advance_schedule,
    gazebo_to_enu_position,
    gazebo_to_enu_quaternion,
    gazebo_to_enu_yaw,
    wrap_angle,
)


CONFIG = {
    'gps_position_stddev': [0.6, 0.6, 0.9],
    'gps_outlier_min_m': 5.0,
    'gps_outlier_max_m': 8.0,
    'vo_scale_stddev': 0.01,
    'vo_initial_velocity_bias_stddev': 0.02,
    'vo_velocity_bias_random_walk_stddev': 0.001,
    'vo_velocity_noise_stddev': 0.03,
    'vo_position_step_noise_stddev': 0.003,
    'vo_initial_yaw_rate_bias_stddev': math.radians(0.2),
    'vo_yaw_bias_random_walk_stddev': math.radians(0.01),
    'vo_yaw_step_noise_stddev': math.radians(0.03),
    'vo_pose_position_noise_stddev': 0.01,
    'vo_pose_yaw_noise_stddev': math.radians(0.3),
}


def make_sequence(seed):
    """Generate a compact representative corruption sequence."""
    model = SensorCorruptor(seed, CONFIG)
    output = []
    for index in range(100):
        stamp = index * 0.01
        position = np.array([0.01 * index, 0.002 * index, 2.0])
        state = model.advance(position, 0.001 * index, stamp)
        if index % 20 == 0:
            output.extend(model.gps_measurement(position))
            output.extend(model.noisy_vo_sample().position)
            output.append(state.yaw)
    return np.asarray(output)


def test_gazebo_to_mavros_enu_spawn_transform():
    """The documented spawn converts to the observed MAVROS ENU pose."""
    transformed = gazebo_to_enu_position([13.0, 7.0, 0.0])
    assert np.allclose(transformed, [-7.0, 13.0, 0.0])
    assert math.isclose(gazebo_to_enu_yaw(0.0), math.pi / 2.0)
    quaternion = gazebo_to_enu_quaternion([0.0, 0.0, 0.0, 1.0])
    assert np.allclose(
        quaternion,
        [0.0, 0.0, math.sqrt(0.5), math.sqrt(0.5)],
    )


def test_angle_wrapping():
    """Angles always remain in the chosen half-open interval."""
    assert math.isclose(wrap_angle(3.0 * math.pi), -math.pi)
    assert -math.pi <= wrap_angle(100.0) < math.pi


def test_equal_seeds_reproduce_corruption():
    """An equal seed reproduces every hidden bias and noise sample."""
    assert np.array_equal(make_sequence(42), make_sequence(42))


def test_changed_seed_changes_hidden_bias_and_noise():
    """A changed seed changes the corruption trace."""
    assert not np.array_equal(make_sequence(42), make_sequence(43))


def test_reset_restores_rng_and_corruption_state():
    """A time-reset equivalent restores the initial RNG and clears VO."""
    model = SensorCorruptor(42, CONFIG)
    first = model.gps_measurement([1.0, 2.0, 3.0])
    model.advance([0.0, 0.0, 0.0], 0.0, 0.0)
    model.advance([1.0, 0.0, 0.0], 0.1, 1.0)
    model.reset()
    repeated = model.gps_measurement([1.0, 2.0, 3.0])
    assert np.array_equal(first, repeated)
    assert not model.initialized


def test_outlier_has_configured_extra_magnitude():
    """The injected component lies inside the configured magnitude range."""
    normal = SensorCorruptor(7, CONFIG)
    outlier = SensorCorruptor(7, CONFIG)
    regular_measurement = normal.gps_measurement([0.0, 0.0, 0.0])
    outlier_measurement = outlier.gps_measurement(
        [0.0, 0.0, 0.0], outlier=True)
    extra = np.linalg.norm(outlier_measurement - regular_measurement)
    assert CONFIG['gps_outlier_min_m'] <= extra
    assert extra <= CONFIG['gps_outlier_max_m']


def test_vo_drifts_but_remains_finite():
    """VO develops seeded drift without producing invalid state."""
    model = SensorCorruptor(42, CONFIG)
    for index in range(1001):
        state = model.advance(
            [0.01 * index, 0.0, 2.0], 0.0, index * 0.01)
    assert np.all(np.isfinite(state.position))
    assert math.isfinite(state.yaw)
    assert not np.allclose(state.position, [10.0, 0.0, 2.0])


def test_rates_are_scheduled_in_simulation_time():
    """A 100 Hz truth input produces 5 Hz GPS and 30 Hz VO on average."""
    gps_deadline = None
    vo_deadline = None
    gps_count = 0
    vo_count = 0
    for index in range(1000):
        stamp = index * 0.01
        due, gps_deadline = advance_schedule(
            gps_deadline, 1.0 / 5.0, stamp)
        gps_count += int(due)
        due, vo_deadline = advance_schedule(
            vo_deadline, 1.0 / 30.0, stamp)
        vo_count += int(due)
    assert gps_count == 50
    assert vo_count == 300
