

## Gemini key for planning

The `story`, `summary` and `deep-news` commands plan their scenes with Gemini (default model `gemini-3.1-pro-preview`; override with `MIRAGE_PLANNER_MODEL`). Put a key restricted to the Generative Language API in `~/.config/mirage/.env` (chmod 600):

```
GEMINI_API_KEY=...
```

Images, video, voice, music and research come from the sibling tools (lumina, vidius, gen-tts, gen-music, deep-research), each with its own key.
