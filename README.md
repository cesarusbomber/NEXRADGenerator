# Bordeaux Radar Image Generator

This Python script generates realistic synthetic radar images simulating various radar products for a storm near Bordeaux, France. It supports static images and animated GIFs, with several weather radar visualization features.

---

## Features

- **Radar Products:**
  - Composite Reflectivity (default)
  - Storm Relative Velocity with gate-to-gate shear highlights
  - Differential Reflectivity (ZDR)
  - Correlation Coefficient (CC)
  - Spectrum Width (SW)

- **Precipitation Tails:** Directional streaks extending from reflectivity lobes to mimic rain/hail shafts swept by wind.

- **Storm Attributes Panel:** Displays max reflectivity, estimated hail size, rotation strength, and Tornado Vortex Signature (TVS) probability in a sidebar.

- **Severe Weather Polygon:** Optional semi-transparent yellow polygon representing a severe thunderstorm warning area.

- **Gate-to-Gate Shear Highlights:** In velocity products, high shear regions are highlighted in magenta.

- **Animated GIF Support:** Create rotating storm animations with customizable frame count.

- **Background Map Support:** Uses `image.png` as the radar base map if available; otherwise, a dark background is used.

---

## Requirements

- Python 3.x
- Pillow (`pip install pillow`)

---

## Usage

python3 radar.py [options]

| Option             | Description                                                                                  | Example                 |
| ------------------ | -------------------------------------------------------------------------------------------- | ----------------------- |
| `--stageN`         | Storm stage (1 to 3). Controls storm size, reflectivity lobes, and intensity scale.          | `--stage2`              |
| `--intensityX`     | Intensity level (1 to 99). Controls precipitation/hail intensity scale.                      | `--intensity75`         |
| `--productPRODUCT` | Radar product to generate. Options:                                                          |                         |
|                    | - `REFLECTIVITY` (default)                                                                   | `--productREFLECTIVITY` |
|                    | - `VELOCITY` (storm relative velocity with GTG shear highlights)                             | `--productVELOCITY`     |
|                    | - `ZDR` (Differential Reflectivity)                                                          | `--productZDR`          |
|                    | - `CC` (Correlation Coefficient)                                                             | `--productCC`           |
|                    | - `SW` (Spectrum Width)                                                                      | `--productSW`           |
| `--polygon`        | Enable overlay of a semi-transparent severe thunderstorm warning polygon on the radar image. | `--polygon`             |
| `--gif`            | Generate an animated GIF instead of a static PNG image.                                      | `--gif`                 |
| `--framesN`        | Number of frames in the animated GIF. Defaults to 20 if not specified.                       | `--frames30`            |
