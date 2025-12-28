# Mirage: AI Atmospheric Experience Generator

## Project Overview
**Mirage** is an automated generative art pipeline that creates immersive "Atmospheric Forecasts." By combining real-time weather data, AI-scripted podcasts, generative imagery, and seamless video animation, Mirage builds a complete sensory experience for any location on Earth.

## Key Files
*   **`src/mirage/main.py`**: The core orchestration engine and CLI entry point.
*   **`src/mirage/config.py`**: Pydantic-based configuration management.
*   **`src/mirage/templates/`**: Jinja2 templates for HTML generation.
*   **`output/`**: (Default) Directory where generated experiences are stored.

## Usage

### Weather Experience
Generate a multimedia weather report with podcast, art, and optional video.

**Basic Usage:**
```bash
mirage weather
```

**Custom Location:**
```bash
mirage weather -l "Kyoto, Japan"
```

**Video Mode:**
Enable the video generation step (takes longer, creates a motion background):
```bash
mirage weather -l "Times Square" -v
```

**Background Mode:**
Run in the background, detached from the terminal:
```bash
mirage weather -l "Paris" -v -s -b
```

**Silent Mode:**
Run without verbose output:
```bash
mirage weather -s
```

## Configuration
Mirage looks for a configuration file at `~/.config/mirage/.env`.
You can override default settings, tool paths, and output directories there.

Example `.env`:
```bash
DEFAULT_LOCATION="New York, NY"
OUTPUT_BASE_DIR="/home/user/Documents/Mirage"
```

## Dependencies
Mirage relies on the following CLI tools being available in your system path:
*   `atmos`: Weather data fetching.
*   `gen-tts`: Gemini-powered text-to-speech.
*   `lumina`: Gemini-powered image generation.
*   `vidius`: Vertex AI VEO video generation.
*   `convert` (ImageMagick): Fallback image processing.
