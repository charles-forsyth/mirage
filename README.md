# Mirage

AI video and audio experiences built from Chuck's generation tools: lumina (images), vidius (Veo video),
gen-tts (voices), gen-music (Lyria), deep-research and atmos. Mirage plans, calls those tools, and edits
the result with ffmpeg.

## Commands

| Command | What it makes | Typical cost |
|---|---|---|
| `hybrid` | Presenter video: one narrator voice, scene stills with slow camera moves, a few Veo hero shots, music, captions | ~$2 (16 lines, 3 Lite heroes) |
| `weather` | HTML page with a two-voice weather podcast, art and optional background video | ~$0.30, +$0.40 with `-v` |
| `research` | HTML documentary page: research, podcast, music, art | ~$2.50 (Deep Research) |
| `news-short` | Vertical news short: voice, one looping clip, music | ~$0.60 |
| `deep-news` | 16:9 narrated report with a still per segment | ~$2 (Deep Research) + ~$0.07 per segment |
| `story` | Character story, one 6 s Veo clip per line | ~$0.30 per line on Lite |
| `summary` | Character-presented summary, one 6 s Veo clip per line | ~$0.30 per line on Lite |
| `character` | Manage the character library (`list`, `add`, `create`, `remove`) | $0.13 per `create` |

Costs are estimates from Gemini API list prices (see `src/mirage/costs.py`); the GCP billing export is the
source of truth.

## Hybrid mode (recommended)

```
mirage hybrid "HPC and AI news this week" -c Henrietta                # vertical, ~2 min, ~$2
mirage hybrid "Autumn on the homestead" -c Henrietta --heroes 0        # stills only, ~$1.20
mirage hybrid "Grove onboarding" -c director --cinema --source notes.md
mirage hybrid "..." --estimate                                         # print the cost and stop
mirage hybrid "..." --budget 3                                         # refuse to start above $3
mirage hybrid "..." --resume ~/Documents/Mirage/Hybrid_...             # finish a failed run for free
```

How it saves money:

- **One narration track** from Gemini Flash TTS (about 3 cents a minute) instead of Veo speaking every
  line. The voice stays the same all the way through.
- **Stills with motion.** Each line gets a Nano Banana 2 image (~$0.07) animated with a free ffmpeg
  zoom/drift.
- **Few, short, cheap hero shots.** Only `--heroes` lines (default 3) become Veo clips, on the Lite tier
  ($0.05/s), at the shortest length that covers the line (4, 6 or 8 s), with Veo audio off.
- **Quick research** with Gemini Flash + Google Search (a few cents) unless you ask for `--research deep`.
- **Resume.** Every image, clip and voice line is kept; rerunning with `--resume` only makes what is missing.
- **Small files.** Final encode is capped at 4 Mbit/s with loudness normalized to -16 LUFS.

Presenter shots pass the character portrait as a reference image, so the character keeps its look while
appearing in new scenes. Captions are burned in and written to `captions.srt`. A character JSON may set
`"tts_voice"` (a Gemini TTS voice name such as `Aoede`) to fix its narration voice.

## Cost controls for the older modes

- `--tier lite|fast|standard` (global flag, before the command) sets the Veo tier. Default is `lite`.
  Config: `VIDEO_TIER=` in `~/.config/mirage/.env`.
- `summary --research quick|deep` (default quick).
- Story and summary clips are 6 s instead of 8 s; b-roll and segment stills use Nano Banana 2.
- Music beds use the cheaper 30 s Lyria clip and loop under the voice.
- All topics and generated text are shell-quoted, so apostrophes and quotes no longer break runs.
- `deep-news` now researches the topic you give it.

Veo prices (per second, 720p, with audio): Lite $0.05, Fast $0.10, Standard $0.40.

## Keys

The planner uses its own Gemini key in `~/.config/mirage/.env` (chmod 600):

```
GEMINI_API_KEY=...
```

Planner model defaults to `gemini-3.1-pro-preview` (`MIRAGE_PLANNER_MODEL` to override); quick research
uses `gemini-3.8-flash` (`RESEARCH_MODEL=`). The sibling tools each use their own restricted key.
