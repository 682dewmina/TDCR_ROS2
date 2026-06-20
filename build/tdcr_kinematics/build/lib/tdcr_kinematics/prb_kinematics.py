"""
prb_kinematics.py
Pseudo-Rigid-Body kinematics for a 4-module universal joint
tendon-driven continuum robot (TDCR).

Each module has 2 DOF: pitch (theta) and yaw (psi).
Total: 4 modules x 2 DOF = 8 DOF.
"""

import numpy as np
from scipy.optimize import minimize


# ── Robot parameters ─────────────────────────────────────────
L       = 0.065   # link length per module (metres)
D       = 0.012   # cable offset from central axis (metres)
N_MOD   = 4       # number of universal joint modules
N_DOF   = 8       # total degrees of freedom (2 per module)
N_CABLE = 3       # number of actuation cables


# ── Transformation matrices ───────────────────────────────────

def rot_x(theta):
    """4x4 rotation about X axis (pitch)."""
    c, s = np.cos(theta), np.sin(theta)
    return np.array([
        [1,  0,  0,  0],
        [0,  c, -s,  0],
        [0,  s,  c,  0],
        [0,  0,  0,  1]
    ])


def rot_y(psi):
    """4x4 rotation about Y axis (yaw)."""
    c, s = np.cos(psi), np.sin(psi)
    return np.array([
        [ c,  0,  s,  0],
        [ 0,  1,  0,  0],
        [-s,  0,  c,  0],
        [ 0,  0,  0,  1]
    ])


def trans_z(length):
    """4x4 translation along Z axis."""
    T = np.eye(4)
    T[2, 3] = length
    return T


# ── Forward Kinematics ────────────────────────────────────────

def forward_kinematics(joint_angles):
    """
    Compute tip position from joint angles.

    Parameters
    ----------
    joint_angles : array-like, shape (8,)
        [theta1, psi1, theta2, psi2, ..., theta4, psi4]
        theta = pitch (rotation about X)
        psi   = yaw   (rotation about Y)

    Returns
    -------
    tip_pos : np.ndarray, shape (3,)
        Cartesian position of arm tip [x, y, z] in metres
    T_tip : np.ndarray, shape (4, 4)
        Full homogeneous transform from base to tip
    """
    T = np.eye(4)
    for i in range(N_MOD):
        theta = joint_angles[2 * i]       # pitch
        psi   = joint_angles[2 * i + 1]   # yaw
        T = T @ rot_x(theta) @ rot_y(psi) @ trans_z(L)
    tip_pos = T[:3, 3]
    return tip_pos, T

def forward_kinematics_chain(joint_angles):
    """
    Returns the cumulative transform at each disc along the chain,
    from base (T[0] = identity) to tip (T[N_MOD]).
    Needed for geometric cable length computation.
    """
    transforms = [np.eye(4)]
    T = np.eye(4)
    for i in range(N_MOD):
        theta = joint_angles[2 * i]
        psi   = joint_angles[2 * i + 1]
        T = T @ rot_x(theta) @ rot_y(psi) @ trans_z(L)
        transforms.append(T.copy())
    return transforms

# ── Inverse Kinematics ────────────────────────────────────────

def inverse_kinematics(target_pos, initial_angles=None):
    """
    Solve IK numerically using constrained optimisation.

    Parameters
    ----------
    target_pos : array-like, shape (3,)
        Desired Cartesian tip position [x, y, z] in metres
    initial_angles : array-like, shape (8,) or None
        Initial joint angle guess. Defaults to zero (straight).

    Returns
    -------
    result.x : np.ndarray, shape (8,)
        Optimal joint angles [theta1, psi1, ..., theta4, psi4]
    error : float
        Final tip position error in metres
    success : bool
        True if optimiser converged
    """
    if initial_angles is None:
        initial_angles = np.zeros(N_DOF)

    target = np.array(target_pos)

    def cost(angles):
        tip, _ = forward_kinematics(angles)
        return np.linalg.norm(tip - target)

    # Joint angle limits: ±45 degrees per joint
    limit = np.deg2rad(45)
    bounds = [(-limit, limit)] * N_DOF

    result = minimize(
        cost,
        initial_angles,
        method='SLSQP',
        bounds=bounds,
        options={'ftol': 1e-6, 'maxiter': 500}
    )

    tip, _ = forward_kinematics(result.x)
    error = np.linalg.norm(tip - target)

    return result.x, error, result.success


# ── Cable Jacobian ────────────────────────────────────────────

def compute_cable_lengths(joint_angles):
    """
    Geometric cable length: sum of 3D distances between consecutive
    cable attachment points along the chain. Properly accounts for
    lever-arm coupling — an upstream joint moves all downstream
    attachment points, giving each module distinct influence.

    Parameters
    ----------
    joint_angles : array-like, shape (8,)

    Returns
    -------
    cable_lengths : np.ndarray, shape (3,)
    """
    cable_angles = np.array([0.0, 2 * np.pi / 3, 4 * np.pi / 3])
    transforms = forward_kinematics_chain(joint_angles)
    cable_lengths = np.zeros(N_CABLE)

    for j, alpha in enumerate(cable_angles):
        p_local = np.array([D * np.cos(alpha),
                             D * np.sin(alpha),
                             0.0, 1.0])
        total = 0.0
        for i in range(N_MOD):
            P_i   = transforms[i]     @ p_local
            P_ip1 = transforms[i + 1] @ p_local
            total += np.linalg.norm(P_ip1[:3] - P_i[:3])
        cable_lengths[j] = total

    return cable_lengths


def compute_jacobian(joint_angles, delta=1e-5):
    """
    Numerically compute the 3x8 cable Jacobian via
    finite differences.

    J[i,j] = d(cable_i) / d(angle_j)

    Parameters
    ----------
    joint_angles : array-like, shape (8,)
    delta : float
        Finite difference step size

    Returns
    -------
    J : np.ndarray, shape (3, 8)
    """
    J = np.zeros((N_CABLE, N_DOF))
    angles = np.array(joint_angles, dtype=float)

    for j in range(N_DOF):
        a_plus  = angles.copy(); a_plus[j]  += delta
        a_minus = angles.copy(); a_minus[j] -= delta
        l_plus  = compute_cable_lengths(a_plus)
        l_minus = compute_cable_lengths(a_minus)
        J[:, j] = (l_plus - l_minus) / (2 * delta)

    return J


# ── Utility ───────────────────────────────────────────────────

def workspace_check(target_pos):
    """
    Quick check whether a target position is reachable.
    Based on maximum arm reach = N_MOD * L.
    """
    max_reach = N_MOD * L
    dist = np.linalg.norm(target_pos)
    return dist <= max_reach
