# ZIBIDI Quadruped Robot

ZIBIDI is an open-source quadruped robot that can be fabricated with readily available 3D-printable parts and off-the-shelf electronics. This repository aggregates the printable models and documentation needed to assemble a robot powered by a Raspberry Pi 4B and a PCA9685 PWM servo controller.

Thingiverse page for the printable parts: https://www.thingiverse.com/thing:4600316

## Project Overview

The robot uses 12 servo motors (3 per leg) to achieve 3 degrees of freedom in each limb. A Raspberry Pi 4B serves as the primary computer, handling high-level gait generation, while a PCA9685 16-channel PWM driver generates the servo control signals. The Pi communicates with the PCA9685 over the I2C bus, freeing CPU resources for perception and control algorithms.

Key subsystems:

* **Mechanical** – 3D printed chassis, legs, and covers (see the `3d-printable-files` directory for STL files).
* **Electronics** – Raspberry Pi 4B, PCA9685 servo driver, power distribution board, 12 × hobby servos (MG996R or similar), and a 2S/3S LiPo battery with a 6 V BEC.
* **Software** – Python-based control stack using Adafruit's CircuitPython libraries for the PCA9685. The included script demonstrates how to map joint angles to servo pulse widths and run basic standing and walking motions.

## Bill of Materials

The [BOM-ZIBIDI.xlsx](./BOM-ZIBIDI.xlsx) file lists reference components for the mechanical build. The additional electronics below integrate the Raspberry Pi and PCA9685:

| Quantity | Component | Notes |
| --- | --- | --- |
| 1 | Raspberry Pi 4 Model B (2 GB+ RAM) | Runs Linux-based control software. |
| 1 | MicroSD card (32 GB+) | With Raspberry Pi OS. |
| 1 | PCA9685 16-Channel 12-bit PWM Driver | I2C address selectable via A0–A5 jumpers; default `0x40`. |
| 12 | Metal-gear servos (MG996R or equivalent) | Ensure 180° range and 6 V operation. |
| 1 | 5–6 V / 5 A BEC or DC-DC regulator | Powers servos from LiPo battery. |
| 1 | 2S or 3S LiPo battery (2200 mAh+) | Connect through BEC to PCA9685 V+ rail. |
| 1 | Logic-level shifter (optional) | Pi GPIO is 3.3 V; PCA9685 accepts 3.3 V I2C directly. |
| — | Dupont jumper wires, screw terminals, power switch | For wiring and power management. |

## Mechanical Assembly

1. Print the STL files from `3d-printable-files/V4.0` for the latest leg design (or `V3.0` for the earlier variant).
2. Clean and post-process the parts as needed (sanding, removing supports).
3. Assemble each leg: mount three servos per leg to provide hip roll, hip pitch, and knee pitch joints.
4. Route servo cables through the chassis, labeling each channel (e.g., `FR_HIP_ROLL`, `FR_HIP_PITCH`, etc.).
5. Mount the Raspberry Pi and PCA9685 board on the equipment plate; ensure airflow and cable clearance.
6. Install the top cover once the electronics and wiring are tested.

> **Tip:** Keep servo horns centered before installation. Power the servos from a calibration fixture, send a 1500 µs pulse, and mechanically align each leg to its neutral pose.

## Electronics & Wiring

```
Raspberry Pi 4B        PCA9685 Board
------------------     -------------------------------
3.3V (pin 1)  ------>  VCC (logic power)
GND (pin 6)   ------>  GND
SDA (pin 3)   ------>  SDA
SCL (pin 5)   ------>  SCL

External 6 V BEC  --->  V+ rail on PCA9685 (servo power)
External BEC GND  --->  GND (shared with Pi)
Servos            --->  PCA9685 output channels 0–11
```

* Keep the Raspberry Pi powered from its USB-C supply or a regulated 5 V rail. Do **not** power the Pi directly from the servo supply.
* Use ferrite beads or twisted pairs on servo power leads to reduce noise.
* Add a large electrolytic capacitor (≥1000 µF, 10 V) across the PCA9685 V+ and GND pins to smooth current spikes.

## Software Setup

1. Flash Raspberry Pi OS (64-bit) onto the microSD card and boot the Pi.
2. Enable the I2C interface using `sudo raspi-config` → *Interface Options* → *I2C*.
3. Update packages and install Python tooling:

   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv i2c-tools
   sudo usermod -aG i2c $USER
   reboot
   ```

4. Clone this repository onto the Pi and install the software dependencies:

   ```bash
   git clone https://github.com/<your-user>/zibidi.git
   cd zibidi/software
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

5. Verify the PCA9685 is visible on the I2C bus:

   ```bash
   sudo i2cdetect -y 1
   ```

   You should see `0x40` (or your configured address) in the scan output.

6. Run the controller demo:

   ```bash
   python zibidi_controller.py
   ```

   The script stands the robot up, cycles a weight-shift routine, and then returns to a neutral pose. Modify the `GAITS` dictionary for additional motion experiments.

## Calibrating Servos

1. Start with the robot supported in the air so the feet do not touch the ground.
2. Use the `--calibrate` flag in `zibidi_controller.py` to command each joint to a neutral 90° position. Adjust the servo horn on the spline until the limb matches the mechanical neutral.
3. Enter measured offsets (in degrees) into the `SERVO_OFFSETS` dictionary.
4. Repeat for all 12 joints.

## Advanced Development Ideas

* Integrate an IMU (e.g., BNO085) for balance control; connect over I2C and fuse sensor data with complementary or Kalman filtering.
* Port gait generation to ROS 2 and publish joint trajectories using `trajectory_msgs/JointTrajectory` messages.
* Add a depth camera or stereo vision module to the Raspberry Pi and implement terrain-aware foot placement.
* Experiment with reinforcement learning policies trained in simulation (Isaac Gym, PyBullet) and deployed on the Pi.

## Contributing

Pull requests are welcome! Please include wiring diagrams, improved gaits, or additional software modules that extend the robot's capabilities.

