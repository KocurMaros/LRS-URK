"""Deterministic coordinate conversion and sensor-corruption models."""

import math
from dataclasses import dataclass

import numpy as np


def wrap_angle(angle):
    """Wrap an angle to [-pi, pi)."""
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def gazebo_to_enu_position(position):
    """Rotate a Gazebo world position into the MAVROS-compatible ENU frame."""
    position = np.asarray(position, dtype=float)
    return np.array([-position[1], position[0], position[2]], dtype=float)


def gazebo_to_enu_yaw(yaw):
    """Rotate a Gazebo world yaw into the MAVROS-compatible ENU frame."""
    return wrap_angle(yaw + math.pi / 2.0)


def multiply_quaternions(left, right):
    """Multiply two x, y, z, w quaternions."""
    lx, ly, lz, lw = left
    rx, ry, rz, rw = right
    return np.array([
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry - lx * rz + ly * rw + lz * rx,
        lw * rz + lx * ry - ly * rx + lz * rw,
        lw * rw - lx * rx - ly * ry - lz * rz,
    ])


def gazebo_to_enu_quaternion(quaternion):
    """Rotate a Gazebo orientation into the MAVROS-compatible ENU frame."""
    rotated = multiply_quaternions(
        yaw_to_quaternion(math.pi / 2.0),
        np.asarray(quaternion, dtype=float),
    )
    norm = np.linalg.norm(rotated)
    if norm < 1e-12:
        return yaw_to_quaternion(math.pi / 2.0)
    return rotated / norm


def yaw_to_quaternion(yaw):
    """Return an x, y, z, w quaternion for a yaw rotation."""
    return np.array([0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)])


def quaternion_to_yaw(quaternion):
    """Extract yaw from an x, y, z, w quaternion."""
    x, y, z, w = quaternion
    sin_yaw = 2.0 * (w * z + x * y)
    cos_yaw = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(sin_yaw, cos_yaw)


def rotate_world_to_body(vector, yaw):
    """Rotate a three-dimensional ENU vector into the yaw-only body frame."""
    c = math.cos(yaw)
    s = math.sin(yaw)
    x, y, z = vector
    return np.array([c * x + s * y, -s * x + c * y, z])


def rotate_body_to_world(vector, yaw):
    """Rotate a three-dimensional yaw-only body vector into ENU."""
    c = math.cos(yaw)
    s = math.sin(yaw)
    x, y, z = vector
    return np.array([c * x - s * y, s * x + c * y, z])


def advance_schedule(deadline, period, stamp):
    """Return whether a sample is due and the next simulation-time deadline."""
    if deadline is None:
        deadline = stamp
    due = stamp + 1e-9 >= deadline
    if due:
        while deadline <= stamp + 1e-9:
            deadline += period
    return due, deadline


@dataclass(frozen=True)
class VoState:
    """Current corrupted visual-odometry state."""

    position: np.ndarray
    yaw: float
    body_velocity: np.ndarray


class SensorCorruptor:
    """Stateful, seeded GPS and visual-odometry corruption model."""

    def __init__(self, seed, config):
        """Create a model whose full output is reproducible from ``seed``."""
        self.seed = int(seed)
        self.config = config
        self.reset()

    def reset(self):
        """Restore the RNG and all corruption state to their initial values."""
        self.rng = np.random.default_rng(self.seed)
        self.initialized = False
        self.last_time = None
        self.last_true_position = None
        self.last_true_yaw = None
        self.vo_position = None
        self.vo_yaw = None
        self.vo_body_velocity = np.zeros(3)
        self.vo_scale = None
        self.vo_velocity_bias = None
        self.vo_yaw_rate_bias = None

    def initialize(self, position, yaw, stamp):
        """Start the VO track at the true pose with hidden, seeded biases."""
        self.last_true_position = np.asarray(position, dtype=float).copy()
        self.last_true_yaw = float(yaw)
        self.last_time = float(stamp)
        self.vo_position = self.last_true_position.copy()
        self.vo_yaw = self.last_true_yaw
        self.vo_body_velocity = np.zeros(3)
        self.vo_scale = 1.0 + self.rng.normal(
            0.0, self.config['vo_scale_stddev'])
        self.vo_velocity_bias = self.rng.normal(
            0.0, self.config['vo_initial_velocity_bias_stddev'], 3)
        self.vo_yaw_rate_bias = self.rng.normal(
            0.0, self.config['vo_initial_yaw_rate_bias_stddev'])
        self.initialized = True

    def advance(self, position, yaw, stamp):
        """Advance the drifting VO track using a new true pose."""
        position = np.asarray(position, dtype=float)
        stamp = float(stamp)
        if not self.initialized:
            self.initialize(position, yaw, stamp)
            return self.vo_state()

        dt = stamp - self.last_time
        if dt <= 0.0:
            return self.vo_state()

        true_world_step = position - self.last_true_position
        true_body_step = rotate_world_to_body(
            true_world_step, self.last_true_yaw)
        step_noise = self.rng.normal(
            0.0,
            self.config['vo_position_step_noise_stddev'] * math.sqrt(dt),
            3,
        )
        corrupted_body_step = (
            self.vo_scale * true_body_step
            + self.vo_velocity_bias * dt
            + step_noise
        )
        self.vo_position += rotate_body_to_world(
            corrupted_body_step, self.vo_yaw)
        true_yaw_step = wrap_angle(yaw - self.last_true_yaw)
        yaw_noise = self.rng.normal(
            0.0,
            self.config['vo_yaw_step_noise_stddev'] * math.sqrt(dt),
        )
        self.vo_yaw = wrap_angle(
            self.vo_yaw + true_yaw_step
            + self.vo_yaw_rate_bias * dt + yaw_noise)
        self.vo_body_velocity = corrupted_body_step / dt

        sqrt_dt = math.sqrt(dt)
        self.vo_velocity_bias += self.rng.normal(
            0.0,
            self.config['vo_velocity_bias_random_walk_stddev'] * sqrt_dt,
            3,
        )
        self.vo_yaw_rate_bias += self.rng.normal(
            0.0,
            self.config['vo_yaw_bias_random_walk_stddev'] * sqrt_dt,
        )
        self.last_true_position = position.copy()
        self.last_true_yaw = float(yaw)
        self.last_time = stamp
        return self.vo_state()

    def vo_state(self):
        """Return a copy of the current VO track state."""
        return VoState(
            self.vo_position.copy(),
            self.vo_yaw,
            self.vo_body_velocity.copy(),
        )

    def noisy_vo_sample(self):
        """Sample the reported VO pose and body velocity."""
        state = self.vo_state()
        position = state.position + self.rng.normal(
            0.0, self.config['vo_pose_position_noise_stddev'], 3)
        yaw = wrap_angle(state.yaw + self.rng.normal(
            0.0, self.config['vo_pose_yaw_noise_stddev']))
        body_velocity = state.body_velocity + self.rng.normal(
            0.0, self.config['vo_velocity_noise_stddev'], 3)
        return VoState(position, yaw, body_velocity)

    def gps_measurement(self, position, outlier=False):
        """Sample GPS position, optionally with one large innovation."""
        position = np.asarray(position, dtype=float)
        sigma = np.asarray(self.config['gps_position_stddev'], dtype=float)
        measurement = position + self.rng.normal(0.0, sigma, 3)
        if outlier:
            direction = self.rng.normal(0.0, 1.0, 3)
            norm = np.linalg.norm(direction)
            if norm < 1e-12:
                direction = np.array([1.0, 0.0, 0.0])
            else:
                direction /= norm
            magnitude = self.rng.uniform(
                self.config['gps_outlier_min_m'],
                self.config['gps_outlier_max_m'],
            )
            measurement += magnitude * direction
            offset = measurement - position
            offset_norm = np.linalg.norm(offset)
            minimum = self.config['gps_outlier_min_m']
            if 1e-12 < offset_norm < minimum:
                measurement = position + offset * minimum / offset_norm
            elif offset_norm <= 1e-12:
                measurement = position + np.array([minimum, 0.0, 0.0])
        return measurement
