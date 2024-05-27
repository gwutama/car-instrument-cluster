#!/usr/bin/env python

import pygame
import math
import can
import threading

# Initialize Pygame
pygame.init()

# Set up the display
width, height = 1200, 600
window = pygame.display.set_mode((width, height))
pygame.display.set_caption("Instrument Cluster")

# Colors
BLACK = (0, 0, 0)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
RED_ORANGE = (255, 51, 0)
DARK_RED_ORANGE = (128, 26, 0)
BLUE_PURPLE = (128, 0, 255)
DARK_PURPLE = (51, 0, 102)
LIGHT_PURPLE = (204, 153, 255)

# Fonts
font_path = './conthrax-sb.otf'
large_font = pygame.font.Font(font_path, 55)
normal_font = pygame.font.Font(font_path, 20)
small_font = pygame.font.Font(font_path, 14)

# Speedometer and RPM Gauge Positions
speedometer_center = (300, 300)  # Scaled by 1.5x
tachometer_center = (900, 300)  # Scaled by 1.5x
radius = 225  # Scaled by 1.5x

# Speed and RPM (initial values)
speed = 0
rpm = 0

# CAN interface setup
# Use 'socketcan' as the bustype when possible, otherwise use 'virtual'
bus = None

try:
    bus = can.interface.Bus(bustype='socketcan', channel='vcan0', bitrate=500000)
except:
    print("Error: CAN FD not supported. Using virtual CAN.")
    bus = can.interface.Bus(bustype='virtual', channel='vcan0', bitrate=500000)

def receive_can_data():
    global speed, rpm
    while True:
        message = bus.recv()
        if message.arbitration_id == 0x1A0:
            speed = int.from_bytes(message.data[0:2], byteorder='little') * 0.103
        elif message.arbitration_id == 0x0AA:
            rpm = int.from_bytes(message.data[4:6], byteorder='little') * 0.25

# Start CAN data reception in a separate thread
can_thread = threading.Thread(target=receive_can_data)
can_thread.start()

def draw_fps_counter(clock):
    # Draw FPS counter
    fps = clock.get_fps()
    fps_text = small_font.render(f'FPS: {int(fps)}', True, DARK_GRAY)
    window.blit(fps_text, (width - fps_text.get_width() - 10, height - fps_text.get_height() - 10))  # 10 pixels from the bottom right corner

def draw_glow(center, inner_radius, outer_radius, color):
    for i in range(outer_radius - inner_radius):
        alpha = 255 - int(255 * (1 - i / (outer_radius - inner_radius)))
        glow_color = (color[0], color[1], color[2], alpha)
        glow_surface = pygame.Surface((outer_radius*2, outer_radius*2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surface, glow_color, (outer_radius, outer_radius), outer_radius - i, 1)
        window.blit(glow_surface, (center[0] - outer_radius, center[1] - outer_radius))

def draw_circle(center, radius, color, border_color=None, border_width=3):
    pygame.draw.circle(window, color, center, radius)
    if border_color:
        pygame.draw.circle(window, border_color, center, radius, border_width)

def draw_gauge(center, value, max_value, tick_min_value, tick_max_value, tick_step, label = ''):
    # Draw glowing effect
    draw_glow(center, radius, radius + 20, BLUE_PURPLE)

    # Draw needle
    angle = math.radians((value / max_value) * 270 - 225)
    x = center[0] + (radius - 40) * math.cos(angle)
    y = center[1] + (radius - 40) * math.sin(angle)
    pygame.draw.line(window, BLUE_PURPLE, center, (x, y), 7)

    # Draw center circle
    draw_circle(center, 130, BLACK, border_color=BLUE_PURPLE, border_width=1)
    draw_glow(center, 130, 180, DARK_PURPLE)

    # Draw main ticks and in-between ticks
    for i in range(tick_min_value, tick_max_value + 1, tick_step):
        tick_color = RED_ORANGE if i >= tick_max_value - 2 * tick_step else LIGHT_GRAY
        in_between_tick_color = DARK_RED_ORANGE if i > tick_max_value - 3 * tick_step else DARK_GRAY

        angle = math.radians(((i - tick_min_value) / (tick_max_value - tick_min_value)) * 270 - 225)
        x1 = center[0] + (radius - 30 * 0.8) * math.cos(angle)  # 20% shorter
        y1 = center[1] + (radius - 30 * 0.8) * math.sin(angle)  # 20% shorter
        x2 = center[0] + radius * math.cos(angle)
        y2 = center[1] + radius * math.sin(angle)
        pygame.draw.line(window, tick_color, (x1, y1), (x2, y2), 3)

        # Draw in-between ticks
        if i < tick_max_value:  # No in-between tick after the last main tick
            in_between_angle = math.radians(((i + tick_step / 2 - tick_min_value) / (tick_max_value - tick_min_value)) * 270 - 225)
            in_between_x1 = center[0] + (radius - 20 * 0.8) * math.cos(in_between_angle)  # 20% shorter
            in_between_y1 = center[1] + (radius - 20 * 0.8) * math.sin(in_between_angle)  # 20% shorter
            in_between_x2 = center[0] + radius * math.cos(in_between_angle)
            in_between_y2 = center[1] + radius * math.sin(in_between_angle)
            pygame.draw.line(window, in_between_tick_color, (in_between_x1, in_between_y1), (in_between_x2, in_between_y2), 1)  # Thinner line

        # Draw numbers on the gauge
        text_x = center[0] + (radius - 60) * math.cos(angle)
        text_y = center[1] + (radius - 60) * math.sin(angle)
        number_text = small_font.render(str(i), True, DARK_GRAY)
        window.blit(number_text, (text_x - number_text.get_width() / 2, text_y - number_text.get_height() / 2))

    # Draw label
    label_text = large_font.render(f'{int(value)} {label}', True, LIGHT_GRAY)
    window.blit(label_text, (center[0] - label_text.get_width() // 2 + 10, center[1] - label_text.get_height() // 2))


# Main loop
running = True
clock = pygame.time.Clock()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Clear the screen
    window.fill(BLACK)

    # Draw gauges
    draw_gauge(speedometer_center, speed, 280, 0, 280, 20)
    draw_gauge(tachometer_center, rpm, 8000, 1, 8, 1)

    draw_fps_counter(clock)

    # Update display
    pygame.display.flip()

    # Cap the frame rate
    clock.tick(60)

pygame.quit()

