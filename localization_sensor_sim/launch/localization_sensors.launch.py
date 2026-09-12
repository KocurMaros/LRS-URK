"""Bridge Gazebo inputs and start the localisation sensor simulator."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    """Return the bridge and seeded sensor simulator launch description."""
    package_share = get_package_share_directory('localization_sensor_sim')
    default_parameters = os.path.join(package_share, 'config', 'sensors.yaml')
    parameters_file = LaunchConfiguration('params_file')
    random_seed = LaunchConfiguration('seed')

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='localization_gz_bridge',
        output='screen',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/evaluation/ground_truth_gz@nav_msgs/msg/Odometry'
            '[gz.msgs.Odometry',
            '/localization/imu_gz@sensor_msgs/msg/Imu[gz.msgs.IMU',
        ],
        remappings=[
            ('/evaluation/ground_truth_gz',
             '/localization/_ground_truth_raw'),
            ('/localization/imu_gz', '/localization/_imu_raw'),
        ],
    )

    simulator = Node(
        package='localization_sensor_sim',
        executable='sensor_simulator',
        name='sensor_simulator',
        output='screen',
        parameters=[
            parameters_file,
            {'random_seed': ParameterValue(random_seed, value_type=int)},
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'params_file',
            default_value=default_parameters,
            description='Sensor corruption parameter YAML file',
        ),
        DeclareLaunchArgument(
            'seed',
            default_value='42',
            description='Seed for GPS and VO corruption',
        ),
        bridge,
        simulator,
    ])
