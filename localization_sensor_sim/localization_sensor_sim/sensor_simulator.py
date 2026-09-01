"""ROS 2 node that publishes the Assignment 2 localisation sensor contract."""

import copy
import math

import numpy as np
import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
from std_srvs.srv import SetBool, Trigger

from localization_sensor_sim.sensor_model import (
    SensorCorruptor,
    advance_schedule,
    gazebo_to_enu_position,
    gazebo_to_enu_quaternion,
    quaternion_to_yaw,
    yaw_to_quaternion,
)


def stamp_to_seconds(stamp):
    """Convert builtin_interfaces/Time to floating-point seconds."""
    return float(stamp.sec) + float(stamp.nanosec) * 1e-9


def set_diagonal(covariance, values):
    """Set the six diagonal entries of a ROS 6x6 covariance array."""
    for index, value in zip((0, 7, 14, 21, 28, 35), values):
        covariance[index] = float(value)


class LocalizationSensorSimulator(Node):
    """Generate reproducible GPS and VO from Gazebo ground truth."""

    def __init__(self):
        """Create publishers, private subscriptions, and test services."""
        super().__init__('sensor_simulator')
        self._declare_parameters()
        self._read_parameters()

        self.truth_publisher = self.create_publisher(
            Odometry, '/evaluation/ground_truth', qos_profile_sensor_data)
        self.gps_publisher = self.create_publisher(
            PoseWithCovarianceStamped,
            '/localization/gps',
            qos_profile_sensor_data,
        )
        self.vo_publisher = self.create_publisher(
            Odometry, '/localization/vo', qos_profile_sensor_data)
        self.imu_publisher = self.create_publisher(
            Imu, '/localization/imu', qos_profile_sensor_data)

        self.truth_subscription = self.create_subscription(
            Odometry,
            '/localization/_ground_truth_raw',
            self._truth_callback,
            qos_profile_sensor_data,
        )
        self.imu_subscription = self.create_subscription(
            Imu,
            '/localization/_imu_raw',
            self._imu_callback,
            qos_profile_sensor_data,
        )

        self.create_service(
            SetBool, '/localization/set_gps_enabled', self._set_gps_enabled)
        self.create_service(
            SetBool, '/localization/set_vo_enabled', self._set_vo_enabled)
        self.create_service(
            Trigger,
            '/localization/inject_gps_outlier',
            self._inject_gps_outlier,
        )

        self.gps_enabled = True
        self.vo_enabled = True
        self.inject_outlier = False
        self.last_sim_time = None
        self.next_gps_time = None
        self.next_vo_time = None
        self.corruptor = SensorCorruptor(self.random_seed, self.model_config)
        self.get_logger().info(
            'Localisation sensors ready with random seed '
            f'{self.random_seed}')

    def _declare_parameters(self):
        self.declare_parameter('random_seed', 42)
        self.declare_parameter('gps_rate_hz', 5.0)
        self.declare_parameter('gps_position_stddev', [0.6, 0.6, 0.9])
        self.declare_parameter('gps_outlier_min_m', 5.0)
        self.declare_parameter('gps_outlier_max_m', 8.0)
        self.declare_parameter('vo_rate_hz', 30.0)
        self.declare_parameter('vo_scale_stddev', 0.01)
        self.declare_parameter(
            'vo_initial_velocity_bias_stddev', 0.02)
        self.declare_parameter(
            'vo_velocity_bias_random_walk_stddev', 0.001)
        self.declare_parameter('vo_velocity_noise_stddev', 0.03)
        self.declare_parameter('vo_position_step_noise_stddev', 0.003)
        self.declare_parameter(
            'vo_initial_yaw_rate_bias_stddev', math.radians(0.2))
        self.declare_parameter(
            'vo_yaw_bias_random_walk_stddev', math.radians(0.01))
        self.declare_parameter(
            'vo_yaw_step_noise_stddev', math.radians(0.03))
        self.declare_parameter('vo_pose_position_noise_stddev', 0.01)
        self.declare_parameter(
            'vo_pose_yaw_noise_stddev', math.radians(0.3))
        self.declare_parameter('imu_yaw_rate_variance', 1.6e-5)
        self.declare_parameter('required_gps_outage_s', 15.0)
        self.declare_parameter('suggested_vo_outage_s', 3.0)

    def _read_parameters(self):
        def value(name):
            return self.get_parameter(name).value

        self.random_seed = int(value('random_seed'))
        self.gps_period = 1.0 / float(value('gps_rate_hz'))
        self.vo_period = 1.0 / float(value('vo_rate_hz'))
        self.imu_yaw_rate_variance = float(
            value('imu_yaw_rate_variance'))
        names = (
            'gps_position_stddev',
            'gps_outlier_min_m',
            'gps_outlier_max_m',
            'vo_scale_stddev',
            'vo_initial_velocity_bias_stddev',
            'vo_velocity_bias_random_walk_stddev',
            'vo_velocity_noise_stddev',
            'vo_position_step_noise_stddev',
            'vo_initial_yaw_rate_bias_stddev',
            'vo_yaw_bias_random_walk_stddev',
            'vo_yaw_step_noise_stddev',
            'vo_pose_position_noise_stddev',
            'vo_pose_yaw_noise_stddev',
        )
        self.model_config = {name: value(name) for name in names}

    def _reset_for_time_jump(self):
        self.corruptor.reset()
        self.last_sim_time = None
        self.next_gps_time = None
        self.next_vo_time = None
        self.inject_outlier = False
        self.get_logger().warning(
            'Simulation time moved backwards; corruption state and RNG reset')

    def _truth_callback(self, raw):
        stamp = stamp_to_seconds(raw.header.stamp)
        if (self.last_sim_time is not None
                and stamp < self.last_sim_time - 1e-9):
            self._reset_for_time_jump()
        self.last_sim_time = stamp

        raw_position = raw.pose.pose.position
        position = gazebo_to_enu_position(
            [raw_position.x, raw_position.y, raw_position.z])
        raw_orientation = raw.pose.pose.orientation
        orientation = gazebo_to_enu_quaternion([
            raw_orientation.x,
            raw_orientation.y,
            raw_orientation.z,
            raw_orientation.w,
        ])
        yaw = quaternion_to_yaw(orientation)

        self._publish_truth(raw, position, orientation)
        self.corruptor.advance(position, yaw, stamp)

        gps_due, self.next_gps_time = advance_schedule(
            self.next_gps_time, self.gps_period, stamp)
        if gps_due:
            if self.gps_enabled:
                self._publish_gps(raw.header.stamp, position)

        vo_due, self.next_vo_time = advance_schedule(
            self.next_vo_time, self.vo_period, stamp)
        if vo_due:
            if self.vo_enabled:
                self._publish_vo(raw.header.stamp)

    def _publish_truth(self, raw, position, orientation):
        truth = copy.deepcopy(raw)
        truth.header.frame_id = 'map'
        truth.child_frame_id = 'base_link'
        truth.pose.pose.position.x = float(position[0])
        truth.pose.pose.position.y = float(position[1])
        truth.pose.pose.position.z = float(position[2])
        truth.pose.pose.orientation.x = float(orientation[0])
        truth.pose.pose.orientation.y = float(orientation[1])
        truth.pose.pose.orientation.z = float(orientation[2])
        truth.pose.pose.orientation.w = float(orientation[3])
        raw_linear = raw.twist.twist.linear
        truth.twist.twist.linear.x = -raw_linear.y
        truth.twist.twist.linear.y = raw_linear.x
        truth.twist.twist.linear.z = raw_linear.z
        raw_angular = raw.twist.twist.angular
        truth.twist.twist.angular.x = -raw_angular.y
        truth.twist.twist.angular.y = raw_angular.x
        truth.twist.twist.angular.z = raw_angular.z
        self.truth_publisher.publish(truth)

    def _publish_gps(self, stamp, position):
        message = PoseWithCovarianceStamped()
        message.header.stamp = stamp
        message.header.frame_id = 'map'
        measured = self.corruptor.gps_measurement(
            position, outlier=self.inject_outlier)
        self.inject_outlier = False
        message.pose.pose.position.x = float(measured[0])
        message.pose.pose.position.y = float(measured[1])
        message.pose.pose.position.z = float(measured[2])
        message.pose.pose.orientation.w = 1.0
        sigma = np.asarray(
            self.model_config['gps_position_stddev'], dtype=float)
        set_diagonal(
            message.pose.covariance,
            [sigma[0] ** 2, sigma[1] ** 2, sigma[2] ** 2,
             1e6, 1e6, 1e6],
        )
        self.gps_publisher.publish(message)

    def _publish_vo(self, stamp):
        state = self.corruptor.noisy_vo_sample()
        message = Odometry()
        message.header.stamp = stamp
        message.header.frame_id = 'vo_odom'
        message.child_frame_id = 'base_link'
        message.pose.pose.position.x = float(state.position[0])
        message.pose.pose.position.y = float(state.position[1])
        message.pose.pose.position.z = float(state.position[2])
        quaternion = yaw_to_quaternion(state.yaw)
        message.pose.pose.orientation.x = float(quaternion[0])
        message.pose.pose.orientation.y = float(quaternion[1])
        message.pose.pose.orientation.z = float(quaternion[2])
        message.pose.pose.orientation.w = float(quaternion[3])
        message.twist.twist.linear.x = float(state.body_velocity[0])
        message.twist.twist.linear.y = float(state.body_velocity[1])
        message.twist.twist.linear.z = float(state.body_velocity[2])
        pose_position_var = (
            self.model_config['vo_pose_position_noise_stddev'] ** 2)
        pose_yaw_var = self.model_config['vo_pose_yaw_noise_stddev'] ** 2
        velocity_var = self.model_config['vo_velocity_noise_stddev'] ** 2
        set_diagonal(
            message.pose.covariance,
            [pose_position_var] * 3 + [1e6, 1e6, pose_yaw_var],
        )
        set_diagonal(
            message.twist.covariance,
            [velocity_var] * 3 + [1e6, 1e6, 1e6],
        )
        self.vo_publisher.publish(message)

    def _imu_callback(self, raw):
        message = Imu()
        message.header = raw.header
        message.header.frame_id = 'base_link'
        message.orientation_covariance[0] = -1.0
        message.linear_acceleration_covariance[0] = -1.0
        message.angular_velocity.z = raw.angular_velocity.z
        message.angular_velocity_covariance[0] = 1e6
        message.angular_velocity_covariance[4] = 1e6
        message.angular_velocity_covariance[8] = (
            self.imu_yaw_rate_variance)
        self.imu_publisher.publish(message)

    def _set_gps_enabled(self, request, response):
        self.gps_enabled = bool(request.data)
        response.success = True
        state = 'enabled' if self.gps_enabled else 'disabled'
        response.message = f'GPS {state}'
        return response

    def _set_vo_enabled(self, request, response):
        self.vo_enabled = bool(request.data)
        response.success = True
        state = 'enabled' if self.vo_enabled else 'disabled'
        response.message = f'VO {state}'
        return response

    def _inject_gps_outlier(self, request, response):
        del request
        self.inject_outlier = True
        response.success = True
        response.message = (
            'The next enabled GPS sample will contain an outlier')
        return response


def main(args=None):
    """Run the localisation sensor simulator."""
    rclpy.init(args=args)
    node = LocalizationSensorSimulator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
