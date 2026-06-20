import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('tdcr_description')
    urdf_file = os.path.join(pkg_share, 'robot.urdf')
    rviz_config = os.path.join(pkg_share, 'rviz', 'tdcr_view.rviz')

    with open(urdf_file, 'r') as f:
        robot_description = f.read()

    rviz_args = ['-d', rviz_config] if os.path.exists(rviz_config) else []

    return LaunchDescription([

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': False
            }]
        ),

        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            output='screen'
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=rviz_args
        ),

    ])
