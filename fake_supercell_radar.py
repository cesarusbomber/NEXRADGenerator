#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import math
import random
import sys
from datetime import datetime
import time
import os

WIDTH, HEIGHT = 1024, 1024
CENTER_X, CENTER_Y = WIDTH // 2, HEIGHT // 2
RADAR_NAME = "Bordeaux KBDX (KRAD Bordeaux)"
BLIND_SPOT_RADIUS = 24

REFLECTIVITY_COLORS = [
    (0, 5, (0, 0, 0)),
    (5, 20, (0, 100, 0)),
    (20, 30, (255, 255, 0)),
    (30, 40, (255, 165, 0)),
    (40, 50, (255, 0, 0)),
    (50, 60, (139, 0, 0)),
    (60, 80, (128, 0, 128)),
]

VELOCITY_COLORS = [
    (-120, -80, (0, 0, 139)),
    (-80, -60, (0, 0, 255)),
    (-60, -40, (135, 206, 235)),
    (-40, -20, (255, 255, 255)),
    (-20, 0, (255, 182, 193)),
    (0, 20, (255, 105, 180)),
    (20, 40, (255, 20, 147)),
    (40, 60, (139, 0, 0)),
    (60, 120, (128, 0, 128)),
]

def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

def get_color_from_table(value, color_table):
    for low, high, color in color_table:
        if low <= value < high:
            return color
    return color_table[-1][2]

def get_text_size(font, text):
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def draw_grid(draw, spacing=80):
    ring_color = (60, 60, 60)
    for r in range(spacing, WIDTH // 2, spacing):
        draw.ellipse([
            CENTER_X - r, CENTER_Y - r,
            CENTER_X + r, CENTER_Y + r
        ], outline=ring_color, width=1)

    for angle_deg in range(0, 360, 30):
        angle_rad = math.radians(angle_deg)
        x = CENTER_X + math.cos(angle_rad) * (WIDTH // 2)
        y = CENTER_Y + math.sin(angle_rad) * (HEIGHT // 2)
        draw.line([CENTER_X, CENTER_Y, x, y], fill=ring_color, width=1)

def add_speckle_noise(pixels, chance=0.002):
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if random.random() < chance:
                noise = random.randint(150, 255)
                pixels[x, y] = (noise, noise, noise)

def generate_reflectivity_image(stage=1, intensity=50):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    pixels = img.load()

    max_reflectivity = [35, 55, 75][stage - 1] * (intensity / 99)
    storm_radius = [200, 280, 360][stage - 1]
    num_lobes = [1, 2, 3][stage - 1]

    random.seed(int(time.time() // 10))
    lobe_centers = []
    for _ in range(num_lobes):
        cx = CENTER_X + random.randint(-160, 160)
        cy = CENTER_Y + random.randint(-160, 160)
        strength = random.uniform(max_reflectivity * 0.5, max_reflectivity)
        radius = random.randint(80, 160)
        lobe_centers.append((cx, cy, strength, radius))

    hook_lobe = (CENTER_X + int(storm_radius * 0.6), CENTER_Y + 40,
                 max_reflectivity * 0.8, int(storm_radius * 0.6))

    for y in range(HEIGHT):
        for x in range(WIDTH):
            dx = x - CENTER_X
            dy = y - CENTER_Y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > storm_radius:
                continue

            val = max_reflectivity * (1 - dist / storm_radius) ** 2

            for (cx, cy, strength, radius) in lobe_centers:
                d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if d < radius:
                    val += strength * (1 - d / radius) ** 1.5

            angle = math.atan2(dy, dx)
            if -0.9 < angle < 0.3:
                d_hook = math.sqrt((x - hook_lobe[0]) ** 2 + (y - hook_lobe[1]) ** 2)
                if d_hook < hook_lobe[3]:
                    val += hook_lobe[2] * (1 - d_hook / hook_lobe[3]) ** 2

            val += random.uniform(-6, 6) * (intensity / 99)
            val = max(0, min(80, val))

            color = get_color_from_table(val, REFLECTIVITY_COLORS)
            pixels[x, y] = color + (180,)

    add_speckle_noise(pixels, chance=0.001)
    img = img.filter(ImageFilter.GaussianBlur(radius=2.0))
    return img

def generate_velocity_image(stage=1, intensity=50):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    pixels = img.load()

    max_radius = [200, 280, 360][stage - 1]
    velocity_amp = [60, 80, 120][stage - 1] * (intensity / 99)

    random.seed(int(time.time() // 10))

    for y in range(HEIGHT):
        for x in range(WIDTH):
            dx = x - CENTER_X
            dy = y - CENTER_Y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > max_radius:
                continue

            angle = math.atan2(dy, dx)
            base_val = velocity_amp * math.sin(2 * angle) * (1 - dist / max_radius)
            noise = random.uniform(-10, 10) * (intensity / 99)
            val = max(-120, min(120, base_val + noise))

            color = get_color_from_table(val, VELOCITY_COLORS)
            pixels[x, y] = color + (180,)

    add_speckle_noise(pixels, chance=0.001)
    img = img.filter(ImageFilter.GaussianBlur(radius=2.0))
    return img

def overlay_radar_on_map(radar_img):
    map_path = "image.png"
    if os.path.exists(map_path):
        map_img = Image.open(map_path).convert("RGBA")
        map_img = map_img.resize((WIDTH, HEIGHT))
        combined = Image.alpha_composite(map_img, radar_img)
        return combined
    else:
        return radar_img

def draw_colorbar(draw, x, y, width, height, colors, labels, font):
    seg_width = width / len(colors)
    for i, color in enumerate(colors):
        draw.rectangle([x + i * seg_width, y, x + (i + 1) * seg_width, y + height], fill=color)
    for i, label in enumerate(labels):
        label_x = x + i * seg_width - 8
        draw.text((label_x, y + height + 2), label, fill="white", font=font)

def main():
    stage = 1
    intensity = 50
    velocity_mode = False

    for arg in sys.argv[1:]:
        if arg.startswith("--stage"):
            stage = int(arg.replace("--stage", ""))
        elif arg.startswith("--intensity"):
            intensity = max(1, min(99, int(arg.replace("--intensity", ""))))
        elif arg == "--velocity":
            velocity_mode = True

    print(f"[INFO] Generating {'Velocity' if velocity_mode else 'Reflectivity'} image (stage {stage}, intensity {intensity})...")

    radar_img = generate_velocity_image(stage, intensity) if velocity_mode else generate_reflectivity_image(stage, intensity)
    radar_img = overlay_radar_on_map(radar_img)

    draw = ImageDraw.Draw(radar_img)

    try:
        font_small = ImageFont.truetype("arial.ttf", 20)
        font_big = ImageFont.truetype("arial.ttf", 36)
    except:
        font_small = ImageFont.load_default()
        font_big = ImageFont.load_default()

    draw_grid(draw)

    # Radar blind spot
    center = (CENTER_X, CENTER_Y)
    draw.ellipse([
        (center[0] - BLIND_SPOT_RADIUS, center[1] - BLIND_SPOT_RADIUS),
        (center[0] + BLIND_SPOT_RADIUS, center[1] + BLIND_SPOT_RADIUS)],
        fill=(0, 0, 0, 255),
    )

    text_lines = ["KBDX", "(KRAD Bordeaux)"]
    total_text_height = sum(get_text_size(font_small, line)[1] for line in text_lines)
    start_y = center[1] - total_text_height // 2
    for line in text_lines:
        text_width, text_height = get_text_size(font_small, line)
        draw.text((center[0] - text_width // 2, start_y), line, fill="white", font=font_small)
        start_y += text_height

    utcnow = datetime.utcnow()
    timestamp_str = f"{utcnow.month}_{utcnow.day}_{utcnow.year}_{utcnow.strftime('%H%M')}UTC"
    product = "VELOCITYRADIAL" if velocity_mode else "COMPOSITEREFLECTIVITY"

    draw.text((40, 40), f"RADAR: {RADAR_NAME}", fill="white", font=font_big)
    draw.text((40, 90), "Storm Relative Velocity" if velocity_mode else "Composite Reflectivity", fill="white", font=font_big)
    draw.text((40, 140), utcnow.strftime("%Y-%m-%d %H:%M UTC"), fill="white", font=font_big)

    # Colorbar
    if velocity_mode:
        colors = [c for _, _, c in VELOCITY_COLORS]
        labels = ["-120", "-80", "-60", "-40", "-20", "0", "20", "40", "60", "120"]
    else:
        colors = [c for _, _, c in REFLECTIVITY_COLORS]
        labels = ["0", "5", "20", "30", "40", "50", "60", "80"]

    draw_colorbar(draw, 60, HEIGHT - 100, 900, 40, colors, labels, font_small)

    output_filename = f"{timestamp_str}_BORDEAUX_{product}VIEW.png"
    radar_img.save(output_filename)
    print(f"[INFO] Saved image to {output_filename}")

if __name__ == "__main__":
    main()
