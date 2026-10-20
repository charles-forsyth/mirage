# mirage specification

Version 0.15.0 (2026-10-20; code 0.15.0). Owner: Chuck Forsyth.
Repository: `charles-forsyth/mirage` (local checkout `~/Projects/mirage`). License: MIT.

## 1. Purpose and scope

`mirage` is a multimedia AI orchestration CLI that plans, prices, generates, and edits complete audio-visual productions (presenter briefings, code tutorials, atmospheric weather experiences, Deep Research documentaries, news shorts, and character stories) by coordinating five leaf CLI tools and `ffmpeg`:

- `lumina` — character portraits (`gemini-3-pro-image`) and scene stills (`gemini-3.1-flash-image` / Nano Banana 2)
- `vidius` — Veo 3.1 talking-presenter clips and b-roll hero video shots (`veo-3.1-lite-generate-preview` default)
- `gen-tts` — single-speaker narration and multi-speaker podcasts (`gemini-3.8-flash-tts`)
- `gen-music` — instrumental background music beds (`lyria-3-clip-preview`)
- `deep-research` — multi-step grounded web research reports (`--research deep`)
- `atmos` — live Google Maps Platform weather data (for `mirage weather`)
- `ffmpeg` / `ffprobe` — Ken Burns motion (`zoompan`), `fit_clip` / `loop_clip` timing alignment, sidechain/ducked music mixing, burned-in subtitles (`.srt`), loudness normalization (`-16 LUFS`), and H.264 4 Mbit/s output encoding.

## 2. Design decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | Hybrid presenter architecture (`mirage hybrid`) as primary pipeline | All-Veo modes (`story`, `summary`) animate every line with Veo ($5–$22/video) and suffer per-clip voice drift. `hybrid` synthesizes one continuous narrator voice via `gen-tts` (~$0.03/min), renders b-roll as Nano Banana 2 stills ($0.067) with free `ffmpeg` Ken Burns motion or Pillow code slides (`--tutorial`), and uses Veo 3.1 Lite ($0.05/s) only for presenter talking shots and N hero b-roll clips (~$2–$3.40 total). |
| D2 | Every on-camera presenter shot is a talking Veo video (`talking=True`), never a frozen still | Early builds only animated one presenter clip and left subsequent presenter appearances as static images. In `hybrid.py`, every line marked `kind="presenter"` gets `talking=True`, generates an image-to-video Veo clip from a character still with lip-movement prompting, and extends to the narration line's duration via `loop_clip()` (never freezing on the last frame). |
| D3 | Pre-run `--estimate` and post-TTS `--budget` circuit breaker | `estimate_cost()` prints a line-item `Ledger` before spending anything. During a live run, `plan_cost()` prices the actual planned shots and measured TTS durations and aborts before calling `lumina`/`vidius`/`gen-music` if the total exceeds `--budget`. |
| D4 | Idempotent asset caching & `--resume <run_dir>` | Every paid asset (`line_XX.wav`, `scene_XX.png`, `hero_XX.mp4`, `talk_XX.mp4`, `music.wav`, `plan.json`) is checked for non-zero existence before generation. Re-running with `--resume <dir>` skips existing assets and finishes assembly at zero duplicate API cost. |
| D5 | Deterministic Pillow code slides for tutorials (`--tutorial` / `slides.py`) | Image models mangle terminal commands and code syntax. `--tutorial` instructs the planner to emit `kind="screen"` shots copying verbatim commands from `--source`, rendered at 1920x1080 by `slides.render_slide()` with Pillow for $0.00. |
| D6 | Subprocess argument lists everywhere (`media.run(cmd: list[str])`) | Eliminates shell injection and quote/apostrophe breakage when prompts or transcripts contain special characters. |
| D7 | Acronym normalization for burned-in captions (`caption_text()`) | Narration spells acronyms phonetically for TTS (`"A-I"`, `"U R L"`, `"s k dash"`). `caption_text()` restores `"AI"`, `"URL"`, `"sk-"`, `"OpenAI"`, `"401"`, `"429"` before writing `captions.srt`. |

## 3. Architecture

```text
mirage CLI (src/mirage/main.py)
  |-- Settings (src/mirage/config.py)
  |     `-- ~/.config/mirage/.env (GEMINI_API_KEY, default tool paths, output_base_dir)
  |-- Planner & Direct Gemini client (src/mirage/planner.py)
  |     |-- PLANNER_MODEL = gemini-3.1-pro-preview (override via MIRAGE_PLANNER_MODEL)
  |     `-- Sends x-goog-api-key header (never URL query parameter)
  |-- Cost Ledger (src/mirage/costs.py)
  |     `-- VEO_PER_SECOND, IMAGE_MODELS, TTS_PER_SECOND, MUSIC_CLIP, Ledger
  |-- Hybrid Pipeline (src/mirage/hybrid.py)
  |     |-- 1. Research: --source FILE | quick (gemini-3.8-flash + Google Search) | deep (deep-research CLI)
  |     |-- 2. Plan: make_plan() -> plan.json (lines with kind=presenter|broll|screen, talking, hero)
  |     |-- 3. Narration: gen-tts per line -> line_00.wav .. line_N.wav + measured durations
  |     |-- 4. Budget gate: plan_cost(plan, tier, image_model) <= --budget
  |     |-- 5. Visuals (up to 3 retries per leaf call):
  |     |     |-- screen shots -> slides.render_slide() (Pillow 1920x1080 PNG, free)
  |     |     |-- presenter shots -> lumina (character ref) -> vidius (-i scene.png, talking prompt) -> loop_clip()
  |     |     |-- hero b-roll -> vidius (4/6/8s shortest cover) -> fit_clip()
  |     |     `-- still b-roll -> lumina (gemini-3.1-flash-image) -> media.ken_burns()
  |     |-- 6. Music bed: gen-music -d 25 -f wav
  |     `-- 7. Assembly (src/mirage/media.py):
  |           `-- concat clips + ducked music + captions.srt + loudnorm (-16 LUFS, 4 Mbit/s) -> final.mp4
  `-- Legacy / Specialized Modes (main.py)
        |-- weather (-l LOC [-v]) -> atmos + gen-tts podcast + lumina + gen-music -> HTML experience
        |-- research (-t TOPIC)   -> deep-research + gen-tts + lumina + gen-music -> HTML documentary
        |-- news-short (-t TOPIC) -> vertical 9:16 short
        |-- deep-news (-t TOPIC)  -> 16:9 multi-segment report
        |-- story / summary       -> character all-Veo modes
        `-- character {list,add,create,remove} -> ~/.config/mirage/characters/<Name>.{json,png}
```

### Module map

| File | Responsibility |
|---|---|
| `src/mirage/main.py` | Top-level argparse router, character library commands (`list`, `add`, `create`, `remove`), legacy modes (`weather`, `research`, `news-short`, `deep-news`, `story`, `summary`), and `hybrid` subcommand dispatch. |
| `src/mirage/config.py` | `Settings` (`pydantic-settings`) loading `~/.config/mirage/.env`: leaf binary names, `video_tier="lite"`, `image_model="flash"`, `research_model="gemini-3.8-flash"`, `output_base_dir=~/Documents/Mirage`, `character_library_dir=~/.config/mirage/characters`. |
| `src/mirage/hybrid.py` | End-to-end hybrid presenter/tutorial pipeline: `caption_text()`, `hero_duration()`, `estimate_cost()`, `plan_cost()`, `make_plan()`, `_run_retry()`, `run_hybrid()`. |
| `src/mirage/planner.py` | `_post_gemini()` REST helper with exponential backoff on `429/500/503/504` and header-based `x-goog-api-key` authentication; legacy mode planners. |
| `src/mirage/media.py` | `run()`, `probe_duration()`, `ken_burns()`, `fit_clip()`, `loop_clip()`, `concat_clips()`, `mix_audio()`, `burn_captions()`, `write_srt()`. |
| `src/mirage/slides.py` | `render_slide()` — renders 1920x1080 dark-theme terminal/code slides with Pillow for `--tutorial` mode. |
| `src/mirage/costs.py` | List-price constants (`VEO_PER_SECOND`, `IMAGE_MODELS`, `TTS_PER_SECOND`, `MUSIC_CLIP`, `MUSIC_FULL`, `PLANNER_CALL`, `QUICK_RESEARCH`, `DEEP_RESEARCH`) and `Ledger`. |

## 4. Character library schema (`~/.config/mirage/characters/<Name>.json`)

Each character consists of `<Name>.json` and `<Name>.png` in `~/.config/mirage/characters/`:

```json
{
  "name": "Henrietta",
  "description": "A warm, sharp-witted presenter...",
  "voice_prompt": "Warm, articulate, engaging broadcast delivery",
  "tts_voice": "Aoede",
  "image_path": "/Users/charlesforsyth/.config/mirage/characters/Henrietta.png"
}
```

- `tts_voice` (optional, default `"Aoede"` in `hybrid.py`) pins the Gemini TTS prebuilt voice so every narration line uses the exact same voice without style-prompt doubling.

## 5. Cost model (`src/mirage/costs.py`)

| Component | Model / Tool | Unit price (USD) | Typical 16-line Hybrid (Lite) |
|---|---|---|---|
| Script planner | `gemini-3.1-pro-preview` | $0.02 / call | $0.02 |
| Quick research | `gemini-3.8-flash` + Search | $0.03 / call | $0.03 |
| Narration TTS | `gen-tts` (`gemini-3.8-flash-tts`) | $0.0005 / sec | ~$0.05 (~100s) |
| Scene stills | `lumina` (`gemini-3.1-flash-image`) | $0.067 / image | ~$0.94 (14 stills) |
| Veo 3.1 Lite clips | `vidius` (`veo-3.1-lite-generate-preview`) | $0.05 / sec | ~$1.80 (6 clips x 6s) |
| Music bed | `gen-music` (`lyria-3-clip-preview`) | $0.04 / clip | $0.04 |
| **Total** | | | **~$2.88** |

## 6. Configuration (`~/.config/mirage/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | required | Gemini API key for the Mirage planner (`generativelanguage.googleapis.com`). |
| `MIRAGE_PLANNER_MODEL` | `"gemini-3.1-pro-preview"` | Planner model override. |
| `VIDEO_TIER` | `"lite"` | Default Veo tier (`lite`, `fast`, `standard`). |
| `IMAGE_MODEL` | `"flash"` | Default scene still tier (`flash` = `gemini-3.1-flash-image`, `pro` = `gemini-3-pro-image`). |
| `RESEARCH_MODEL` | `"gemini-3.8-flash"` | Grounded quick-research model. |
| `RESEARCH_MODE` | `"quick"` | Default research mode (`quick` or `deep`). |
| `OUTPUT_BASE_DIR` | `~/Documents/Mirage` | Base directory for run folders (`<Mode>_<topic>_<timestamp>`). |
| `CHARACTER_LIBRARY_DIR` | `~/.config/mirage/characters` | Character JSON + portrait directory. |

## 7. CLI interface

```text
mirage [--tier {lite,fast,standard}] <subcommand> ...

Subcommands:
  hybrid [topic]
         [-c CHARACTER | --character CHARACTER]
         [--source FILE]
         [--research {quick,deep}]
         [--lines INT]                  # default: 16
         [--presenters INT]             # default: max(3, round(lines/3))
         [--heroes INT]                 # default: 2 (b-roll video clips)
         [--tier {lite,fast,standard}]
         [--image-model {flash,pro}]
         [--voice VOICE]
         [--cinema]                     # 16:9 widescreen (default: 9:16 vertical)
         [--tutorial]                   # enable Pillow code/command screen slides
         [--estimate]                   # print Ledger cost estimate and exit
         [--budget USD]                 # abort before image/video spend if plan exceeds USD
         [--resume DIR]                 # resume an existing run folder
  character {list,add,create,remove} ...
  weather [-l LOCATION] [-v]
  research -t TOPIC
  news-short -t TOPIC
  deep-news -t TOPIC
  story -t TOPIC -c CHARACTER
  summary -t TOPIC -c CHARACTER [--research {quick,deep}]
```

## 8. Requirements traceability

| ID | Requirement | Verified by |
|---|---|---|
| REQ-CFG-1 | Default settings use `lite` video tier, `flash` image model, and `quick` research mode. | `tests/test_config.py::test_default_settings` |
| REQ-AUTH-1 | Planner sends `GEMINI_API_KEY` via `x-goog-api-key` HTTP header (never in URL query string) to `gemini-3.1-pro-preview`. | `tests/test_config.py::test_planner_uses_header_key_and_current_model` |
| REQ-HYB-1 | `hero_duration()` selects the shortest Veo duration (`4`, `6`, or `8` s) that covers the spoken line. | `tests/test_hybrid.py::test_hero_duration_picks_shortest_veo_length` |
| REQ-HYB-2 | Every presenter line has `talking=True`, and `--heroes` counts b-roll video shots only. | `tests/test_hybrid.py::test_plan_presenters_always_talk_and_heroes_are_broll_only` |
| REQ-HYB-3 | `--budget` aborts `run_hybrid` before any image or video generation if `plan_cost` exceeds the cap. | `tests/test_hybrid.py::test_budget_guard_stops_before_spending` |
| REQ-HYB-4 | Existing non-empty asset files are skipped on `--resume`. | `tests/test_hybrid.py::test_generators_skip_existing_outputs` |
| REQ-SEC-1 | Subprocess execution uses argument lists (`media.run`) so quotes and shell metacharacters in prompts are inert. | `tests/test_hybrid.py::test_run_uses_argument_list_so_quotes_are_safe` |
| REQ-CAP-1 | `caption_text()` converts phonetic TTS spellings (`A-I`, `U R L`, `Open AI`, `four zero one`) back to standard display text (`AI`, `URL`, `OpenAI`, `401`). | `tests/test_hybrid.py::test_caption_text_undoes_tts_spellings` |

## 9. Known gaps and backlog

- **K1 (Confirmed):** Legacy `story` and `summary` modes still animate the character portrait per clip without `--resume` support; porting them onto `hybrid.py`'s asset caching and single-narrator track is planned.
- **K2 (Confirmed):** `deep-news` estimates per-segment image timing from character length rather than `ffprobe`-measured audio duration.
- **K3 (Confirmed):** When `--source` is provided, the planner can occasionally extrapolate numbers not present in the source markdown; adding a post-plan fact-check pass against `--source` is on the backlog.
