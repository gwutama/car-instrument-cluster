#!/usr/bin/env python

import can
import time
import random

# Set up the CAN bus
# Use 'socketcan' as the bustype when possible, otherwise use 'virtual'
bus = None

try:
    bus = can.interface.Bus(bustype='socketcan', channel='vcan0', bitrate=500000)
except:
    print("Error: CAN FD not supported. Using virtual CAN.")
    bus = can.interface.Bus(bustype='virtual', channel='vcan0', bitrate=500000)


# Constants
MAX_SPEED = 180  # Max speed in km/h
RPM_PER_KMH = 25  # Engine RPM increases by 25 for each km/h
IDLE_RPM = 800  # Idle RPM

# Initialize speed and direction
speed = 0
increasing = True


def simulate_speed():
    global speed, increasing

    if increasing:
        speed += random.uniform(0.5, 2.0)  # Increment speed by a small random amount
        if speed >= MAX_SPEED:
            increasing = False
    else:
        speed -= random.uniform(0.5, 5.0)  # Decrement speed by a larger random amount
        if speed <= 0:
            increasing = True
        elif speed < MAX_SPEED / 2:
            if random.random() < 0.1:  # 10% chance to start increasing speed again
                increasing = True

    # Clamp speed to a range of 0 to MAX_SPEED
    speed = max(0, min(MAX_SPEED, speed))

    return speed


def calculate_rpm(speed):
    # Simulate RPM based on speed with some randomness
    rpm = IDLE_RPM + speed * RPM_PER_KMH + random.uniform(-100, 100)
    return max(IDLE_RPM, int(rpm))  # Ensure RPM is at least the idle RPM


def build_can_message_vehicle_speed(speed: int) -> can.Message:
    """
    Builds a CAN message for the given vehicle speed.

    Based on the following excerpt from BMW DBC file:
    BO_ 416 Speed: 8 DSC
      SG_ VehicleSpeed : 0|12@1- (0.103,0) [0|255] "kph" XXX

    :param speed: Vehicle speed in km/h.
    :return: CAN message object.
    """
    # DBC scaling factor for VehicleSpeed
    factor = 0.103

    # Encode the speed using the scaling factor
    raw_value = int(speed / factor)

    # Ensure the raw value fits into 12 bits
    if raw_value < 0 or raw_value > 0xFFF:
        raise ValueError("Speed out of range for 12-bit encoding")

    # Split the raw value into two bytes (little-endian)
    byte1 = (raw_value >> 8) & 0xFF  # Most significant 4 bits
    byte0 = raw_value & 0xFF         # Least significant 8 bits

    # Build the data payload (little-endian)
    data = [byte0, byte1, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

    # Create and return the CAN message
    message = can.Message(arbitration_id=0x1A0, data=data, is_extended_id=False)
    return message


def build_can_message_engine_rpm(rpm: int) -> can.Message:
    """
    Builds a CAN message for the given engine RPM.

    Based on the following excerpt from BWM DBC file:
    BO_ 170 AccPedal: 8 DME
      SG_ EngineSpeed : 32|16@1+ (0.25,0) [0|8000] "rpm" XXX

    :param rpm: Engine RPM.
    :return: CAN message object.
    """
    # DBC scaling factor for EngineSpeed
    factor = 0.25

    # Encode the RPM using the scaling factor
    raw_value = int(rpm / factor)

    # Ensure the raw value fits into 16 bits
    if raw_value < 0 or raw_value > 0xFFFF:
        raise ValueError("RPM out of range for 16-bit encoding")

    # Split the raw value into two bytes (little-endian)
    byte5 = (raw_value >> 8) & 0xFF  # Most significant 8 bits
    byte4 = raw_value & 0xFF         # Least significant 8 bits

    # Build the data payload (EngineSpeed starts at bit 32, which is byte 4)
    data = [0x00, 0x00, 0x00, 0x00, byte4, byte5, 0x00, 0x00]

    # Create and return the CAN message
    message = can.Message(arbitration_id=0x0AA, data=data, is_extended_id=False)
    return message


def send_can_messages():
    speed = simulate_speed()
    rpm = calculate_rpm(speed)

    speed_msg = build_can_message_vehicle_speed(speed)
    rpm_msg = build_can_message_engine_rpm(rpm)

    bus.send(speed_msg)
    bus.send(rpm_msg)


# Send messages every 100ms
try:
    while True:
        send_can_messages()
        time.sleep(0.01)
except KeyboardInterrupt:
    pass

