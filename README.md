# Mirage

AI video and audio experience orchestrator (`v0.15.0`) built atop five dedicated generation CLIs: `lumina` (images), `vidius` (Veo 3.1 video), `gen-tts` (Gemini 3.8 voices), `gen-music` (Lyria music), `deep-research`, and `atmos`, mixed and mastered with `ffmpeg`.

See [SPEC.md](SPEC.md) for the full system specification, hybrid shot model, cost ledger formulas, character schema, and requirement traceability.

## Commands

| Command | What it makes | Typical cost |
|---|---|---|
| `hybrid` | Presenter or tutorial video: one narrator voice, scene stills with Ken Burns motion, Pillow code screens (`--tutorial`), talking presenter clips, Veo b-roll hero shots, ducked music, captions | ~$2.00–$3.40 (Lite) |
| `weather` | HTML page with a two-voice weather podcast, art, and optional background video | ~$0.30, +$0.40 with `-v` |
| `research` | HTML documentary page: Deep Research report, podcast, music, art | ~$2.50 (Deep Research) |
| `news-short` | Vertical 9:16 news short: voice, one looping clip, music | ~$0.60 |
| `deep-news` | 16:9 narrated report with a still per segment | ~$2.00 (Deep Research) + ~$0.07/segment |
| `story` | Character story, one 6 s Veo clip per line | ~$0.30/line on Lite |
| `summary` | Character-presented summary, one 6 s Veo clip per line | ~$0.30/line on Lite |
| `character` | Manage the character library (`list`, `add`, `create`, `remove`) | $0.13 per `create` |

Costs are estimates from Gemini API list prices (see `src/mirage/costs.py`); the GCP billing export is the source of truth.

## Installation

### Prerequisites
- `ffmpeg` and `ffprobe` on `PATH` (`brew install ffmpeg`)
- Sibling `uv` tools installed: `lumina`, `vidius`, `gen-tts`, `gen-music`, `atmos`, `deep-research`

```bash
uv tool install --python 3.12 git+https://github.com/charles-forsyth/mirage.git
```

## Hybrid Mode (Recommended)

```bash
# Vertical 9:16 presenter video (~2 min)
mirage hybrid "HPC and AI news this week" -c Henrietta

# Widescreen 16:9 tutorial with verbatim Pillow code slides from a markdown source
mirage hybrid "Workstation CLI setup" -c Henrietta --cinema --tutorial --source steps.md

# Stills-only b-roll (no b-roll Veo clips)
mirage hybrid "Autumn on the homestead" -c Henrietta --heroes 0

# Estimate cost and shot breakdown without spending
mirage hybrid "Cluster status update" -c Henrietta --source notes.md --estimate

# Enforce a hard spend ceiling (aborts before image/video generation if exceeded)
mirage hybrid "Cluster status update" -c Henrietta --budget 3.00

# Resume an interrupted run (reuses all existing audio/image/video assets for free)
mirage hybrid --resume ~/Documents/Mirage/Hybrid_...
```

### How Hybrid Mode Works
- **Single continuous narrator voice** via `gen-tts` (`gemini-3.8-flash-tts`, ~$0.03/min), pinned by the character's `"tts_voice"` field (default `Aoede`).
- **Every on-camera presenter appearance talks:** Every `presenter` shot renders a character-referenced scene still via `lumina` and animates it with `vidius` (Veo 3.1 Lite) using lip-movement prompting, extended seamlessly with `loop_clip`.
- **Exact code screens (`--tutorial`):** Renders `screen` shots directly with Pillow (`src/mirage/slides.py`) at 1920x1080 so terminal commands and code blocks are pixel-accurate and free.
- **Smart b-roll:** `--heroes` b-roll lines (default 2) become Veo 3.1 Lite video clips at the shortest duration (`4`, `6`, or `8` s) that covers the line; remaining b-roll lines are `gemini-3.1-flash-image` stills ($0.067) with `ffmpeg` Ken Burns motion.
- **Broadcast mixdown:** Ducked Lyria music bed, `.srt` burned-in captions with automatic acronym cleanup (`A-I` -> `AI`, `U R L` -> `URL`), `-16 LUFS` loudness normalization, capped at 4 Mbit/s H.264.

## Configuration & Keys

Mirage reads `~/.config/mirage/.env` (`chmod 600`):

```env
GEMINI_API_KEY=your_mirage_planner_api_key
DEFAULT_LOCATION="New York, NY"
```

Planner model defaults to `gemini-3.1-pro-preview` (override with `MIRAGE_PLANNER_MODEL`); quick grounded research uses `gemini-3.8-flash` (`RESEARCH_MODEL`). Each leaf tool reads its own restricted API key from `~/.config/<tool>/.env`.

## Development

```bash
uv sync --python 3.12
uv run --python 3.12 pytest
uv run --python 3.12 ruff check .
```
