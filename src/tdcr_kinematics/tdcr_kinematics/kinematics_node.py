"""
kinematics_node.py
ROS 2 node wrapping the PRB kinematics library.

Subscribes:  /tdcr/target_pose  (geometry_msgs/Point)
Publishes:   /tdcr/joint_angles (std_msgs/Float64MultiArray)
             /tdcr/cable_lengths(std_msgs/Float64MultiArray)
             /joint_states      (sensor_msgs/JointState)
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
from std_msgs.msg import Float64MultiArray
from sensor_msgs.msg import JointState
from builtin_interfaces.msg import Time
import numpy as np

from tdcr_kinematics.prb_kinematics import (
    forward_kinematics,
    inverse_kinematics,
    compute_cable_lengths,
    compute_jacobian,
    workspace_check
)

# Joint names must match URDF exactly
JOINT_NAMES = [
    'joint1', 'joint2',
    'joint3', 'joint4',
    'joint5', 'joint6',
    'joint7', 'joint8'
]


class KinematicsNode(Node):

    def __init__(self):
        super().__init__('tdcr_kinematics_node')

        # ── Publishers ────────────────────────────────────────
        self.pub_angles = self.create_publisher(
            Float64MultiArray,
            '/tdcr/joint_angles', 10)

        self.pub_cables = self.create_publisher(
            Float64MultiArray,
            '/tdcr/cable_lengths', 10)

        self.pub_joint_states = self.create_publisher(
            JointState,
            '/joint_states', 10)

        # ── Subscriber ────────────────────────────────────────
        self.sub_target = self.create_subscription(
            Point,
            '/tdcr/target_pose',
            self.target_callback, 10)

        # ── State ─────────────────────────────────────────────
        self.current_angles = np.zeros(8)

        self.get_logger().info('TDCR Kinematics Node started')
        self.get_logger().info(
            f'Listening on /tdcr/target_pose')

    def target_callback(self, msg):
        target = [msg.x, msg.y, msg.z]

        # Workspace check
        if not workspace_check(target):
            self.get_logger().warn(
                f'Target {target} outside workspace '
                f'(max reach = 0.26m)')
            return

        # Solve IK
        angles, error, success = inverse_kinematics(
            target,
            initial_angles=self.current_angles
        )

        if not success:
            self.get_logger().warn(
                f'IK failed for target {target} '
                f'(error={error:.4f}m)')
            return

        self.current_angles = angles

        # Compute cable lengths
        cables = compute_cable_lengths(angles)

        # Log result
        self.get_logger().info(
            f'IK solved | error={error*1000:.2f}mm | '
            f'cables={cables.round(4)}')

        # Publish joint angles
        msg_angles = Float64MultiArray()
        msg_angles.data = angles.tolist()
        self.pub_angles.publish(msg_angles)

        # Publish cable lengths
        msg_cables = Float64MultiArray()
        msg_cables.data = cables.tolist()
        self.pub_cables.publish(msg_cables)

        # Publish joint states for robot_state_publisher
        js = JointState()
        js.header.stamp = self.get_clock().now().to_msg()
        js.name     = JOINT_NAMES
        js.position = angles.tolist()
        self.pub_joint_states.publish(js)


def main(args=None):
    rclpy.init(args=args)
    node = KinematicsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
