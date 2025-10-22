"""Basic control routines for the ZIBIDI quadruped robot.

This module provides a command-line interface that can drive 12 servos through
an Adafruit PCA9685 board connected to a Raspberry Pi 4B. It supports
calibrating neutral offsets and executing a small selection of open-loop gaits.

Example
-------
Run the default standing pose and gentle weight-shift routine::

    $ python zibidi_controller.py

Calibrate each joint::

    $ python zibidi_controller.py --calibrate

The calibration command walks through each joint sequentially, waiting for user
confirmation before moving on.
"""

from __future__ import annotations

import argparse
import dataclasses
import time
from typing import Dict, Iterable, List, Tuple

import numpy as np

try:
    from adafruit_servokit import ServoKit
except ImportError as exc:  # pragma: no cover - hardware dependency
    raise SystemExit(
        "adafruit-circuitpython-servokit is required. Install dependencies with "
        "'pip install -r requirements.txt'."
    ) from exc


# The PCA9685 board used by Adafruit's ServoKit has 16 channels. We use 12 for
# the quadruped joints and keep the remaining channels in reserve for grippers
# or sensors.
KIT = ServoKit(channels=16)


@dataclasses.dataclass(frozen=True)
class Joint:
    """Represents a single servo joint on the robot."""

    channel: int
    min_angle: float = -60.0
    max_angle: float = 60.0

    def clamp(self, angle: float) -> float:
        """Clamp ``angle`` to the joint's mechanical limits."""

        return float(np.clip(angle, self.min_angle, self.max_angle))


# Joint ordering follows: [front-right, front-left, rear-right, rear-left] ×
# [hip roll, hip pitch, knee pitch]
JOINTS: Dict[str, Joint] = {
    # Front right (FR)
    "FR_HIP_ROLL": Joint(0, -35, 35),
    "FR_HIP_PITCH": Joint(1, -50, 50),
    "FR_KNEE": Joint(2, -60, 60),
    # Front left (FL)
    "FL_HIP_ROLL": Joint(3, -35, 35),
    "FL_HIP_PITCH": Joint(4, -50, 50),
    "FL_KNEE": Joint(5, -60, 60),
    # Rear right (RR)
    "RR_HIP_ROLL": Joint(6, -35, 35),
    "RR_HIP_PITCH": Joint(7, -50, 50),
    "RR_KNEE": Joint(8, -60, 60),
    # Rear left (RL)
    "RL_HIP_ROLL": Joint(9, -35, 35),
    "RL_HIP_PITCH": Joint(10, -50, 50),
    "RL_KNEE": Joint(11, -60, 60),
}


# Offsets in degrees that align the mechanical neutral pose (legs vertical) with
# the servo controller's 90° neutral position. Modify after running calibration.
SERVO_OFFSETS: Dict[str, float] = {
    name: 0.0 for name in JOINTS
}


# Default stance angles for each joint (in degrees relative to neutral).
STANCE: Dict[str, float] = {
    "FR_HIP_ROLL": 0.0,
    "FR_HIP_PITCH": 10.0,
    "FR_KNEE": -20.0,
    "FL_HIP_ROLL": 0.0,
    "FL_HIP_PITCH": 10.0,
    "FL_KNEE": -20.0,
    "RR_HIP_ROLL": 0.0,
    "RR_HIP_PITCH": 10.0,
    "RR_KNEE": -20.0,
    "RL_HIP_ROLL": 0.0,
    "RL_HIP_PITCH": 10.0,
    "RL_KNEE": -20.0,
}


# Gait keyframes expressed as (duration_seconds, {joint_name: delta_angle}). The
# joint deltas are relative to the neutral stance defined above.
GAITS: Dict[str, List[Tuple[float, Dict[str, float]]]] = {
    "idle_shift": [
        (1.2, {
            "FR_HIP_ROLL": -6.0,
            "RR_HIP_ROLL": -6.0,
            "FL_HIP_ROLL": 6.0,
            "RL_HIP_ROLL": 6.0,
        }),
        (1.2, {
            "FR_HIP_ROLL": 6.0,
            "RR_HIP_ROLL": 6.0,
            "FL_HIP_ROLL": -6.0,
            "RL_HIP_ROLL": -6.0,
        }),
    ],
    "crawl_forward": [
        (0.8, {
            "FR_HIP_PITCH": -8.0,
            "FR_KNEE": 12.0,
        }),
        (0.4, {
            "FR_HIP_PITCH": 4.0,
            "FR_KNEE": -12.0,
            "RR_HIP_PITCH": 4.0,
            "RR_KNEE": -8.0,
        }),
        (0.8, {
            "FL_HIP_PITCH": -8.0,
            "FL_KNEE": 12.0,
        }),
        (0.4, {
            "FL_HIP_PITCH": 4.0,
            "FL_KNEE": -12.0,
            "RL_HIP_PITCH": 4.0,
            "RL_KNEE": -8.0,
        }),
    ],
}


def set_joint_angle(joint_name: str, angle: float) -> None:
    """Set ``joint_name`` to ``angle`` degrees relative to neutral."""

    joint = JOINTS[joint_name]
    target = joint.clamp(angle + SERVO_OFFSETS[joint_name] + 90.0)
    KIT.servo[joint.channel].angle = target


def go_to_pose(pose: Dict[str, float], duration: float, steps: int = 20) -> None:
    """Interpolate to ``pose`` in ``duration`` seconds."""

    current = {name: KIT.servo[joint.channel].angle or 90.0 for name, joint in JOINTS.items()}
    current_rel = {name: angle - (SERVO_OFFSETS[name] + 90.0) for name, angle in current.items()}

    for alpha in np.linspace(0.0, 1.0, steps):
        for joint_name, target_rel in pose.items():
            interpolated = (1 - alpha) * current_rel[joint_name] + alpha * target_rel
            set_joint_angle(joint_name, interpolated)
        time.sleep(duration / steps)


def enter_stance(duration: float = 1.5) -> None:
    """Move the robot into its neutral stance."""

    go_to_pose(STANCE, duration)


def run_gait(gait_name: str, cycles: int) -> None:
    """Execute a gait by name for the requested number of cycles."""

    if gait_name not in GAITS:
        raise ValueError(f"Unknown gait '{gait_name}'. Valid options: {', '.join(GAITS)}")

    keyframes = GAITS[gait_name]
    for _ in range(cycles):
        for duration, deltas in keyframes:
            pose = {name: STANCE.get(name, 0.0) + delta for name, delta in deltas.items()}
            go_to_pose(pose, duration)


def calibrate(order: Iterable[str] | None = None) -> None:
    """Interactively calibrate each joint."""

    if order is None:
        order = JOINTS.keys()

    print("Starting calibration. Ensure the robot is lifted off the ground.")
    for joint_name in order:
        input(f"Press Enter to center {joint_name}...")
        set_joint_angle(joint_name, 0.0)
        print(
            "Adjust the servo horn so the limb is neutral, then record the offset in "
            "SERVO_OFFSETS.")
    print("Calibration routine complete.")


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gait",
        default="idle_shift",
        choices=list(GAITS.keys()),
        help="Open-loop gait to execute after entering stance",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=2,
        help="Number of cycles to run the selected gait",
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Run interactive servo calibration",
    )
    parser.add_argument(
        "--no-stance",
        action="store_true",
        help="Skip moving into the default stance before running the gait",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv)

    if args.calibrate:
        calibrate()
        return 0

    if not args.no_stance:
        enter_stance()

    run_gait(args.gait, args.cycles)
    enter_stance(duration=1.0)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
