# Mirage: AI Atmospheric Experience Generator

## Project Overview
**Mirage** is an automated generative art pipeline that creates immersive "Atmospheric Forecasts." By combining real-time weather data, AI-scripted podcasts, generative imagery, and seamless video animation, Mirage builds a complete sensory experience for any location on Earth.

## Key Files
*   **`mirage.py`**: The core orchestration engine. It executes the following pipeline:
    1.  **Data Gathering**: Fetches real-time weather, astronomy, and alerts using `atmos`.
    2.  **Audio Synthesis**: Generates a "Deep Dive" style weather podcast (`podcast.mp3`) using `gen-tts`.
    3.  **Visual Generation**: Creates a hyper-realistic background image (`background_art.png`) using `lumina`.
    4.  **Motion Synthesis** (Optional): Animates the scene into a seamless loop (`background_video.mp4`) using `vidius`.
    5.  **Experience Assembly**: Compiles everything into a standalone `index.html` with synchronized scrolling data.
*   **`output/`**: Directory where all generated experiences are stored, organized by location and timestamp.

## Usage

### Basic Usage
Generate a standard experience (Audio + Image + Data) for your home location:
```bash
./mirage.py
```

### Custom Location
Generate an experience for a specific place:
```bash
./mirage.py -l "Kyoto, Japan"
```

### Video Mode
Enable the video generation step (takes longer, creates a motion background):
```bash
./mirage.py -l "Times Square" -v
```

### Background Mode
Run the process in the background, detaching it from the terminal immediately. Output is redirected to `mirage.log`.
```bash
./mirage.py -l "Paris" -v -s -b
```

### Silent Mode
Run without verbose output (useful for background tasks or cron jobs):
```bash
./mirage.py -s
```

### Full Example
Generate a full video experience for London, silently, in the background (using manual nohup):
```bash
nohup ./mirage.py -l "London, UK" -v -s > mirage.log 2>&1 &
```

## Dependencies
Mirage relies on the following CLI tools being available in your system path:
*   `atmos`: Weather data fetching.
*   `gen-tts`: Gemini-powered text-to-speech.
*   `lumina`: Gemini-powered image generation.
*   `vidius`: Vertex AI VEO video generation.
*   `convert` (ImageMagick): Fallback image processing.