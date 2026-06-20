"""
jacobian_node.py
Cable Jacobian computation and singularity monitoring for the
4-module, 8-DOF tendon-driven continuum robot (TDCR).

Subscribes:  /tdcr/joint_angles      (std_msgs/Float64MultiArray)
Publishes:   /tdcr/jacobian          (std_msgs/Float64MultiArray, flattened 3x8)
             /tdcr/condition_number  (std_msgs/Float64)
             /tdcr/singularity_warning (std_msgs/Bool)
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray, Float64, Bool
import numpy as np

from tdcr_kinematics.prb_kinematics import compute_jacobian

# Condition number threshold — tune based on workspace testing
SINGULARITY_THRESHOLD = 50.0


class JacobianNode(Node):

    def __init__(self):
        super().__init__('tdcr_jacobian_node')

        # ── Publishers ────────────────────────────────────────
        self.pub_jacobian = self.create_publisher(
            Float64MultiArray,
            '/tdcr/jacobian', 10)

        self.pub_condition = self.create_publisher(
            Float64,
            '/tdcr/condition_number', 10)

        self.pub_singular = self.create_publisher(
            Bool,
            '/tdcr/singularity_warning', 10)

        # ── Subscriber ────────────────────────────────────────
        self.sub_angles = self.create_subscription(
            Float64MultiArray,
            '/tdcr/joint_angles',
            self.angles_callback, 10)

        self.get_logger().info('TDCR Jacobian Node started')
        self.get_logger().info(
            'Listening on /tdcr/joint_angles')

    def angles_callback(self, msg):
        angles = np.array(msg.data)

        if len(angles) != 8:
            self.get_logger().warn(
                f'Expected 8 joint angles, got {len(angles)}')
            return

        # Compute the 3x8 cable Jacobian
        J = compute_jacobian(angles)

        # Singular value decomposition for condition number
        U, S, Vt = np.linalg.svd(J)
        condition_number = S[0] / S[-1] if S[-1] > 1e-9 else float('inf')

        is_singular = condition_number > SINGULARITY_THRESHOLD

        # Log result
        self.get_logger().info(
            f'Jacobian computed | condition={condition_number:.2f} | '
            f'{"SINGULAR" if is_singular else "OK"}')

        # Publish flattened Jacobian (row-major, 3x8 = 24 values)
        msg_J = Float64MultiArray()
        msg_J.data = J.flatten().tolist()
        self.pub_jacobian.publish(msg_J)

        # Publish condition number
        msg_cond = Float64()
        msg_cond.data = float(condition_number)
        self.pub_condition.publish(msg_cond)

        # Publish singularity warning
        msg_warn = Bool()
        msg_warn.data = bool(is_singular)
        self.pub_singular.publish(msg_warn)

        if is_singular:
            self.get_logger().warn(
                f'SINGULARITY WARNING | condition number = '
                f'{condition_number:.2f} exceeds threshold '
                f'{SINGULARITY_THRESHOLD}')


def main(args=None):
    rclpy.init(args=args)
    node = JacobianNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
