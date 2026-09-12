#!/usr/bin/env python3

import threading
import time

import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
from std_srvs.srv import Trigger


class MultiThreadedExecutorDemo(Node):

    def __init__(self):
        super().__init__('mt_executor_demo_python_node')

        self.imu_sim_group = MutuallyExclusiveCallbackGroup()
        self.vision_sim_group = MutuallyExclusiveCallbackGroup()
        self.mavros_imu_group = MutuallyExclusiveCallbackGroup()
        self.synthetic_imu_group = MutuallyExclusiveCallbackGroup()
        self.service_group = MutuallyExclusiveCallbackGroup()
        self.client_group = MutuallyExclusiveCallbackGroup()

        self.imu_sim_count = 0
        self.vision_sim_count = 0

        self.synthetic_imu_pub = self.create_publisher(Imu, 'demo/imu/data', 10)
        self.imu_sim_timer = self.create_timer(
            0.01, self.imu_sim_tick, callback_group=self.imu_sim_group)
        self.vision_sim_timer = self.create_timer(
            0.1, self.vision_sim_tick, callback_group=self.vision_sim_group)

        self.imu_sub = self.create_subscription(
            Imu, 'mavros/imu/data', self.mavros_imu_cb,
            qos_profile_sensor_data, callback_group=self.mavros_imu_group)
        self.synthetic_imu_sub = self.create_subscription(
            Imu, 'demo/imu/data', self.synthetic_imu_cb, 10,
            callback_group=self.synthetic_imu_group)

        self.calibration_service = self.create_service(
            Trigger, 'demo/calibrate_imu', self.calibrate_imu_cb,
            callback_group=self.service_group)
        self.calibration_client = self.create_client(
            Trigger, 'demo/calibrate_imu', callback_group=self.client_group)
        self.service_request_timer = self.create_timer(
            1.0, self.send_calibration_request, callback_group=self.client_group)

        self.get_logger().info(
            'started: timers, mavros IMU, synthetic IMU pub/sub, and calibration service')

    def imu_sim_tick(self):
        self.imu_sim_count += 1
        if self.imu_sim_count % 100 != 0:
            return

        self.get_logger().info(
            f'[imu_sim]    tick {self.imu_sim_count:5d}  thread={threading.get_ident()}')
        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'synthetic_imu'
        msg.linear_acceleration.z = 9.81
        self.synthetic_imu_pub.publish(msg)

    def vision_sim_tick(self):
        time.sleep(0.03)
        self.vision_sim_count += 1
        self.get_logger().info(
            f'[vision_sim] tick {self.vision_sim_count:5d}  thread={threading.get_ident()}')

    def mavros_imu_cb(self, msg):
        self.get_logger().info(
            f'[mavros_imu] accel=({msg.linear_acceleration.x:.2f}, '
            f'{msg.linear_acceleration.y:.2f}, {msg.linear_acceleration.z:.2f})  '
            f'thread={threading.get_ident()}')

    def synthetic_imu_cb(self, msg):
        self.get_logger().info(
            f'[synthetic_imu] accel_z={msg.linear_acceleration.z:.2f}  '
            f'thread={threading.get_ident()}')

    def calibrate_imu_cb(self, request, response):
        del request
        response.success = True
        response.message = 'dummy IMU calibration complete'
        self.get_logger().info(
            f'[service]     IMU calibrated  thread={threading.get_ident()}')
        return response

    def send_calibration_request(self):
        if not self.calibration_client.service_is_ready():
            self.get_logger().info('[client]      waiting for service')
            return

        future = self.calibration_client.call_async(Trigger.Request())
        future.add_done_callback(self.calibration_response_cb)
        self.service_request_timer.cancel()

    def calibration_response_cb(self, future):
        try:
            response = future.result()
            self.get_logger().info(
                f'[client]      response: {response.message}  '
                f'thread={threading.get_ident()}')
        except Exception as error:
            self.get_logger().error(f'[client]      service call failed: {error}')


def main(args=None):
    rclpy.init(args=args)
    node = MultiThreadedExecutorDemo()
    executor = MultiThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
