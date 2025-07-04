#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
import random
import sys
from datetime import datetime
import time
import os

# === Constants ===
WIDTH, HEIGHT = 768, 768
CENTER_X, CENTER_Y = WIDTH // 2, HEIGHT // 2
RADAR_NAME = "Bordeaux KBDX (KRAD Bordeaux)"
BLIND_SPOT_RADIUS = 14

MAP_IMAGE_PATH = "image.png"

# Color tables for products
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
    (-120, -60, (0, 0, 139)),
    (-60, -40, (0, 0, 255)),
    (-40, -20, (135, 206, 235)),
    (-20, 0, (255, 255, 255)),
    (0, 20, (255, 182, 193)),
    (20, 40, (255, 105, 180)),
    (40, 120, (255, 20, 147)),
]

ZDR_COLORS = [
    (-2, -0.5, (128, 0, 128)),
    (-0.5, 0.5, (255, 255, 255)),
    (0.5, 2, (255, 165, 0)),
]

CC_COLORS = [
    (0, 0.6, (255, 0, 0)),
    (0.6, 0.9, (255, 165, 0)),
    (0.9, 1.0, (0, 255, 0)),
]

SW_COLORS = [
    (0, 1, (0, 255, 0)),
    (1, 2, (255, 255, 0)),
    (2, 5, (255, 0, 0)),
]

# Utility functions
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

# === Radar image generators ===

def generate_reflectivity_image(stage=1, intensity=50, rotation=0):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    pixels = img.load()

    max_reflectivity = [35, 55, 75][stage - 1] * (intensity / 99)
    storm_radius = [150, 200, 300][stage - 1]
    num_lobes = [1, 2, 3][stage - 1]

    # Fixed seed for consistency
    random.seed(42)
    lobe_centers = []
    # Position lobes rotating around center
    for i in range(num_lobes):
        angle = rotation + i * (2 * math.pi / num_lobes)
        distance = 80
        cx = CENTER_X + int(math.cos(angle) * distance)
        cy = CENTER_Y + int(math.sin(angle) * distance)
        strength = random.uniform(max_reflectivity * 0.5, max_reflectivity)
        radius = random.randint(40, 80)
        lobe_centers.append((cx, cy, strength, radius))

    # Hook lobe, rotates too
    hook_angle = rotation + 1.5
    hook_lobe = (CENTER_X + int(math.cos(hook_angle) * storm_radius * 0.5),
                 CENTER_Y + int(math.sin(hook_angle) * storm_radius * 0.5),
                 max_reflectivity * 0.8, int(storm_radius * 0.5))

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
                    # Core intensity
                    val += strength * (1 - d / radius) ** 1.5

                    # Precipitation tails
                    tail_vec_x = (x - cx)
                    tail_vec_y = (y - cy)
                    tail_length = 15
                    # Tail points downstream roughly opposite the vector from center to lobe center
                    tail_end_x = x + int(tail_vec_x * tail_length / max(radius,1))
                    tail_end_y = y + int(tail_vec_y * tail_length / max(radius,1))
                    # Draw faded tail pixel on the image
                    # We’ll approximate tail by brightening pixels towards tail_end
                    if 0 <= tail_end_x < WIDTH and 0 <= tail_end_y < HEIGHT:
                        existing = pixels[tail_end_x, tail_end_y]
                        # Increase brightness for tail
                        tail_val = int(min(255, existing[0] + val * 2))
                        pixels[tail_end_x, tail_end_y] = (tail_val, tail_val, 0, 180)

            # Hook lobe contribution
            d_hook = math.sqrt((x - hook_lobe[0]) ** 2 + (y - hook_lobe[1]) ** 2)
            if d_hook < hook_lobe[3]:
                val += hook_lobe[2] * (1 - d_hook / hook_lobe[3]) ** 2

            val += random.uniform(-6, 6) * (intensity / 99)
            val = max(0, min(80, val))

            color = get_color_from_table(val, REFLECTIVITY_COLORS)
            pixels[x, y] = color + (255,)

    add_speckle_noise(pixels)
    img = img.filter(ImageFilter.GaussianBlur(radius=1.2))
    return img

def generate_velocity_image(stage=1, intensity=50, rotation=0):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    pixels = img.load()

    max_radius = [150, 200, 300][stage - 1]
    velocity_amp = [30, 50, 80][stage - 1] * (intensity / 99)

    for y in range(HEIGHT):
        for x in range(WIDTH):
            dx = x - CENTER_X
            dy = y - CENTER_Y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > max_radius:
                continue

            angle = math.atan2(dy, dx) + rotation
            base_val = velocity_amp * math.sin(2 * angle) * (1 - dist / max_radius)
            noise = random.uniform(-10, 10) * (intensity / 99)
            val = max(-120, min(120, base_val + noise))

            color = get_color_from_table(val, VELOCITY_COLORS)
            pixels[x, y] = color + (255,)

    add_speckle_noise(pixels, chance=0.002)
    img = img.filter(ImageFilter.GaussianBlur(radius=1.2))
    return img

def generate_zdr_image(stage=1, intensity=50, rotation=0):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    pixels = img.load()

    radius = [150, 200, 300][stage - 1]

    for y in range(HEIGHT):
        for x in range(WIDTH):
            dx = x - CENTER_X
            dy = y - CENTER_Y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > radius:
                continue

            angle = math.atan2(dy, dx) + rotation
            # Simulate positive ZDR around hail core, low in rain
            val = 1.5 * math.exp(-((dist - 50)/40)**2) * math.cos(angle*3)  
            # Add noise
            val += random.uniform(-0.5, 0.5) * (intensity / 99)
            val = max(-2, min(2, val))

            color = get_color_from_table(val, ZDR_COLORS)
            pixels[x, y] = color + (255,)

    add_speckle_noise(pixels)
    img = img.filter(ImageFilter.GaussianBlur(radius=1.0))
    return img

def generate_cc_image(stage=1, intensity=50, rotation=0):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    pixels = img.load()

    radius = [150, 200, 300][stage - 1]

    for y in range(HEIGHT):
        for x in range(WIDTH):
            dx = x - CENTER_X
            dy = y - CENTER_Y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > radius:
                continue

            # Lower CC inside hail shaft or debris
            val = 0.95 - 0.6 * math.exp(-((dist - 70)/40)**2) * abs(math.sin(rotation*4 + dist/10))
            val += random.uniform(-0.05, 0.05) * (intensity / 99)
            val = max(0, min(1, val))

            color = get_color_from_table(val, CC_COLORS)
            pixels[x, y] = color + (255,)

    add_speckle_noise(pixels, chance=0.001)
    img = img.filter(ImageFilter.GaussianBlur(radius=1.0))
    return img

def generate_sw_image(stage=1, intensity=50, rotation=0):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    pixels = img.load()

    radius = [150, 200, 300][stage - 1]

    for y in range(HEIGHT):
        for x in range(WIDTH):
            dx = x - CENTER_X
            dy = y - CENTER_Y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > radius:
                continue

            # Higher spectrum width near turbulent areas
            val = 3 * math.exp(-((dist - 80)/30)**2) * abs(math.sin(rotation*6 + dist/15))
            val += random.uniform(-0.5, 0.5) * (intensity / 99)
            val = max(0, min(5, val))

            color = get_color_from_table(val, SW_COLORS)
            pixels[x, y] = color + (255,)

    add_speckle_noise(pixels, chance=0.0015)
    img = img.filter(ImageFilter.GaussianBlur(radius=1.0))
    return img

# Gate-to-Gate shear highlight for velocity
def add_gtg_shear_overlay(img, threshold=90):
    pixels = img.load()
    width, height = img.size

    # Create overlay image to mark GTG shear areas
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_pixels = overlay.load()

    # We approximate shear by checking horizontal neighbors' red channel difference
    for y in range(height):
        for x in range(width-1):
            r1, g1, b1, a1 = pixels[x, y]
            r2, g2, b2, a2 = pixels[x+1, y]

            diff = abs(r1 - r2)  # rough proxy for velocity diff

            if diff > threshold:
                # Mark shear pixel bright magenta
                overlay_pixels[x, y] = (255, 0, 255, 180)
                overlay_pixels[x+1, y] = (255, 0, 255, 180)

    return Image.alpha_composite(img, overlay)

# Storm attributes sidebar
def draw_storm_attributes(draw, font_big, font_small, max_reflectivity, hail_size, rotation_strength, tvs_prob):
    panel_width = 220
    x_start = WIDTH - panel_width - 20
    y_start = 20
    box_color = (0, 0, 0, 180)
    text_color = (255, 255, 255)

    # Draw semi-transparent box
    draw.rectangle([x_start, y_start, x_start + panel_width, y_start + 130], fill=box_color)

    # Titles and values
    lines = [
        ("Storm Attributes", None),
        ("Max Reflectivity:", f"{max_reflectivity:.1f} dBZ"),
        ("Estimated Hail Size:", f"{hail_size:.2f} in"),
        ("Rotation Strength:", rotation_strength),
        ("TVS Probability:", f"{tvs_prob}%"),
    ]

    line_y = y_start + 10
    draw.text((x_start + 10, line_y), lines[0][0], font=font_big, fill=text_color)
    line_y += 30

    for label, value in lines[1:]:
        draw.text((x_start + 10, line_y), label, font=font_small, fill=text_color)
        if value:
            text_width, _ = get_text_size(font_small, value)
            draw.text((x_start + panel_width - text_width - 10, line_y), value, font=font_small, fill=text_color)
        line_y += 22

# Generate a polygon for severe thunderstorm warning
def generate_severe_polygon():
    radius = random.randint(120, 200)
    center_angle = random.uniform(0, 2 * math.pi)
    points = []
    for i in range(random.randint(5, 7)):
        angle = center_angle + i * (2 * math.pi / 6) + random.uniform(-0.2, 0.2)
        r = radius + random.randint(-30, 30)
        x = CENTER_X + math.cos(angle) * r
        y = CENTER_Y + math.sin(angle) * r
        points.append((x, y))
    return points

def draw_colorbar(draw, x, y, width, height, colors, labels, font):
    seg_width = width / len(colors)
    for i, color in enumerate(colors):
        draw.rectangle([x + i * seg_width, y, x + (i + 1) * seg_width, y + height], fill=color)
    for i, label in enumerate(labels):
        label_x = x + i * seg_width - 8
        draw.text((label_x, y + height + 2), label, fill="white", font=font)

def main():
    # Default parameters
    stage = 1
    intensity = 50
    product = "REFLECTIVITY"
    polygon_enabled = False
    gif_mode = False
    frames_count = 20

    # Parse args
    for arg in sys.argv[1:]:
        if arg.startswith("--stage"):
            stage = int(arg.replace("--stage", ""))
        elif arg.startswith("--intensity"):
            intensity = max(1, min(99, int(arg.replace("--intensity", ""))))
        elif arg.startswith("--product"):
            product = arg.replace("--product", "").upper()
        elif arg == "--polygon":
            polygon_enabled = True
        elif arg == "--gif":
            gif_mode = True
        elif arg.startswith("--frames"):
            frames_count = int(arg.replace("--frames", ""))

    print(f"[INFO] Generating product {product} (stage {stage}, intensity {intensity})")

    # Storm attributes randomized realistically
    max_reflectivity = random.uniform(40, 78)
    hail_size = random.uniform(0.5, 3.5)
    rotation_strength = random.choice(["Weak", "Moderate", "Strong"])
    tvs_prob = random.randint(30, 99)

    # Load map background
    if os.path.exists(MAP_IMAGE_PATH):
        base_img = Image.open(MAP_IMAGE_PATH).convert("RGBA").resize((WIDTH, HEIGHT))
    else:
        base_img = Image.new("RGBA", (WIDTH, HEIGHT), (30, 30, 30, 255))

    try:
        font_small = ImageFont.truetype("arial.ttf", 14)
        font_big = ImageFont.truetype("arial.ttf", 24)
    except:
        font_small = ImageFont.load_default()
        font_big = ImageFont.load_default()

    def generate_frame(rotation_angle):
        # Generate radar overlay based on product
        if product == "VELOCITY":
            radar_img = generate_velocity_image(stage, intensity, rotation_angle)
            radar_img = add_gtg_shear_overlay(radar_img, threshold=40)  # lower threshold for demo
        elif product == "ZDR":
            radar_img = generate_zdr_image(stage, intensity, rotation_angle)
        elif product == "CC":
            radar_img = generate_cc_image(stage, intensity, rotation_angle)
        elif product == "SW":
            radar_img = generate_sw_image(stage, intensity, rotation_angle)
        else:
            radar_img = generate_reflectivity_image(stage, intensity, rotation_angle)

        combined = Image.alpha_composite(base_img, radar_img)
        draw = ImageDraw.Draw(combined)

        # Draw grid and blind spot
        draw_grid(draw)
        draw.ellipse(
            [
                (CENTER_X - BLIND_SPOT_RADIUS, CENTER_Y - BLIND_SPOT_RADIUS),
                (CENTER_X + BLIND_SPOT_RADIUS, CENTER_Y + BLIND_SPOT_RADIUS),
            ],
            fill=(0, 0, 0, 255),
        )

        # Radar text center label
        text_lines = ["KBDX", "(KRAD Bordeaux)"]
        total_text_height = sum(get_text_size(font_small, line)[1] for line in text_lines)
        start_y = CENTER_Y - total_text_height // 2
        for line in text_lines:
            text_width, text_height = get_text_size(font_small, line)
            draw.text((CENTER_X - text_width // 2, start_y), line, fill="white", font=font_small)
            start_y += text_height

        # Timestamp and titles
        utcnow = datetime.utcnow()
        timestamp_str = f"{utcnow.month}_{utcnow.day}_{utcnow.year}_{utcnow.strftime('%H%M')}UTC"
        product_str = {
            "VELOCITY": "VELOCITYRADIAL",
            "ZDR": "DIFFERENTIALREFLECTIVITY",
            "CC": "CORRELATIONCOEFFICIENT",
            "SW": "SPECTRUMWIDTH",
            "REFLECTIVITY": "COMPOSITEREFLECTIVITY"
        }.get(product, "COMPOSITEREFLECTIVITY")

        draw.text((20, 20), f"RADAR: {RADAR_NAME}", fill="white", font=font_big)
        title_map = {
            "VELOCITY": "Storm Relative Velocity",
            "ZDR": "Differential Reflectivity (ZDR)",
            "CC": "Correlation Coefficient (CC)",
            "SW": "Spectrum Width",
            "REFLECTIVITY": "Composite Reflectivity"
        }
        draw.text((20, 50), title_map.get(product, "Composite Reflectivity"), fill="white", font=font_big)
        draw.text((20, 80), utcnow.strftime("%Y-%m-%d %H:%M UTC"), fill="white", font=font_big)

        # Draw color bar
        if product == "VELOCITY":
            colors = [c for _, _, c in VELOCITY_COLORS]
            labels = ["-120", "-60", "-40", "-20", "0", "20", "40", "120"]
        elif product == "ZDR":
            colors = [c for _, _, c in ZDR_COLORS]
            labels = ["-2", "-0.5", "0.5", "2"]
        elif product == "CC":
            colors = [c for _, _, c in CC_COLORS]
            labels = ["0", "0.6", "0.9", "1"]
        elif product == "SW":
            colors = [c for _, _, c in SW_COLORS]
            labels = ["0", "1", "2", "5"]
        else:
            colors = [c for _, _, c in REFLECTIVITY_COLORS]
            labels = ["0", "5", "20", "30", "40", "50", "60", "80"]

        draw_colorbar(draw, 50, HEIGHT - 80, 660, 30, colors, labels, font_small)

        # Draw severe polygon if enabled
        if polygon_enabled:
            poly_points = generate_severe_polygon()
            overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.polygon(poly_points, outline="yellow", fill=(255, 255, 0, int(255 * 0.4)))
            combined = Image.alpha_composite(combined, overlay)

            # Label polygon
            label_pos = poly_points[0]
            overlay_draw.text((label_pos[0] + 10, label_pos[1] - 10), "Severe Thunderstorm Warning", fill="yellow", font=font_big)

            combined = Image.alpha_composite(combined, overlay)

        # Draw storm attributes sidebar
        draw_storm_attributes(draw, font_big, font_small, max_reflectivity, hail_size, rotation_strength, tvs_prob)

        return combined

    if gif_mode:
        frames = []
        for i in range(frames_count):
            rotation_angle = 2 * math.pi * i / frames_count
            frame = generate_frame(rotation_angle)
            frames.append(frame)
        output_filename = f"BORDEAUX_{product}_GIF_{frames_count}frames_{datetime.utcnow().strftime('%m_%d_%Y_%H%MUTC')}.gif"
        frames[0].save(output_filename, save_all=True, append_images=frames[1:], optimize=False, duration=100, loop=0)
        print(f"[INFO] Saved GIF animation to {output_filename}")
    else:
        frame = generate_frame(0)
        output_filename = f"{datetime.utcnow().strftime('%m_%d_%Y_%H%MUTC')}_BORDEAUX_{product}_VIEW.png"
        frame.convert("RGB").save(output_filename)
        print(f"[INFO] Saved image to {output_filename}")

if __name__ == "__main__":
    main()
