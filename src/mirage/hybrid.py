"""Hybrid presenter videos: one narrator voice, stills with motion, a few Veo hero shots.

Cost model (see costs.py): narration via Gemini Flash TTS (~$0.03/min), scene stills via
Nano Banana 2 (~$0.07 each), Ken Burns motion in ffmpeg (free), Veo only for the
N hero shots on the cheapest tier that looks right (Lite by default), no Veo audio.
"""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path
from typing import Any, Optional

from rich.console import Console

from mirage import costs, media
from mirage.config import settings
from mirage.planner import _post_gemini

console = Console()

DEFAULT_VOICE = "Aoede"


def slug(text: str, n: int = 50) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_")[:n]


def caption_text(line: str) -> str:
    """Undo TTS-friendly spellings for on-screen captions (A-I -> AI, T-P-Us -> TPUs)."""
    line = re.sub(
        r"\b(?:[A-Z]-){1,4}[A-Z](?=s?\b)", lambda m: m.group(0).replace("-", ""), line
    )
    for spoken, shown in (("Open-AI", "OpenAI"), ("x-AI", "xAI"), ("GPT-six", "GPT-6")):
        line = line.replace(spoken, shown)
    return line


def _gemini_json(prompt: str, search: bool = False, model: Optional[str] = None) -> Any:
    payload: dict[str, Any] = {"contents": [{"parts": [{"text": prompt}]}]}
    if search:
        payload["tools"] = [{"google_search": {}}]
    else:
        payload["generationConfig"] = {"responseMimeType": "application/json"}
    import mirage.planner as planner

    old = planner.PLANNER_MODEL
    try:
        if model:
            planner.PLANNER_MODEL = model
        r = _post_gemini(payload).json()
    finally:
        planner.PLANNER_MODEL = old
    text = "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"])
    return text if search else json.loads(text)


def quick_research(topic: str) -> str:
    """Grounded web research with Gemini Flash + Google Search (cents, not dollars)."""
    today = datetime.date.today().isoformat()
    prompt = (
        f"Today is {today}. Research this with Google Search and write a factual briefing "
        f"(about 600 words) with dates and source names for every item. Prefer the last 7 days.\n\nTopic: {topic}"
    )
    return str(_gemini_json(prompt, search=True, model=settings.research_model))


def plan_script(
    source: str, character: dict, lines: int, heroes: int, aspect: str
) -> list[dict]:
    """Turn source material into presenter lines with a shot type per line."""
    orientation = "vertical 9:16" if aspect == "9:16" else "landscape 16:9"
    prompt = f"""
You are the writer and director of a short {orientation} video presented by this character:
{character.get("description", "a friendly presenter")}
Voice: {character.get("voice_prompt", "warm narrator")}

Write exactly {lines} short spoken lines (max 22 words each) covering the source below:
an opening hook, the key facts in order, and a warm sign-off. Keep numbers accurate to the source.
Spell numbers the way they should be spoken.

For each line choose one shot:
- "presenter": the character on camera (use for the opening, sign-off and a few links).
- "broll": a scene illustrating the fact, with no people talking and no text on screen.
Mark exactly {heroes} lines as "hero": true; these get real video motion, so pick the most visual
moments (always include the opening line). All other lines become stills with slow camera moves.

For every line write "visual": a detailed image prompt. For presenter shots, describe the character's
pose, expression and setting. For b-roll, describe the scene photographically.

Return JSON: [{{"line": "...", "shot": "presenter"|"broll", "hero": true|false, "visual": "..."}}]

SOURCE:
{source[:30000]}
"""
    plan = _gemini_json(prompt)
    if not isinstance(plan, list) or not plan:
        raise ValueError("planner returned no lines")
    # Enforce the hero budget regardless of what the model did.
    flagged = [i for i, s in enumerate(plan) if s.get("hero")]
    keep = set(([0] + [i for i in flagged if i != 0])[:heroes]) if heroes else set()
    for i, s in enumerate(plan):
        s["hero"] = i in keep
        s["shot"] = (
            s.get("shot") if s.get("shot") in ("presenter", "broll") else "broll"
        )
    return plan


def estimate(
    n_lines: int,
    heroes: int,
    hero_seconds: int,
    tier: str,
    image_model: str,
    research: str,
    words: int = 18,
    with_music: bool = True,
) -> costs.Ledger:
    led = costs.Ledger()
    if research == "deep":
        led.add(
            "Deep Research agent", 1, costs.DEEP_RESEARCH, "Google estimate $1-3/task"
        )
    elif research == "quick":
        led.add("Quick research (Flash + Search)", 1, costs.QUICK_RESEARCH)
    led.add("Script planner", 1, costs.PLANNER_CALL)
    speech = n_lines * words / costs.WORDS_PER_SECOND
    led.add("Narration TTS (seconds)", speech, round(costs.TTS_PER_SECOND, 5))
    model_id, img_price = costs.IMAGE_MODELS[image_model]
    led.add(
        f"Scene stills ({model_id})", n_lines - heroes if heroes else n_lines, img_price
    )
    if heroes:
        led.add(f"Hero stills ({model_id})", heroes, img_price)
        led.add(
            f"Veo 3.1 {tier} (seconds)",
            heroes * hero_seconds,
            costs.VEO_PER_SECOND[tier],
        )
    if with_music:
        led.add("Music bed (Lyria clip)", 1, costs.MUSIC_CLIP)
    return led


def build(
    topic: str,
    character_name: Optional[str],
    *,
    source_file: Optional[Path] = None,
    research: str = "quick",
    lines: int = 16,
    heroes: int = 3,
    tier: str = "lite",
    image_model: str = "flash",
    aspect: str = "9:16",
    voice: Optional[str] = None,
    with_music: bool = True,
    captions: bool = True,
    budget: Optional[float] = None,
    dry_run: bool = False,
    resume_dir: Optional[Path] = None,
) -> Optional[Path]:
    lib = settings.character_library_dir
    character: dict = {
        "description": character_name or "a friendly narrator",
        "voice_prompt": "warm, clear narrator",
    }
    char_png: Optional[Path] = None
    if character_name:
        meta = lib / f"{character_name}.json"
        if meta.exists():
            character.update(json.loads(meta.read_text()))
        if (lib / f"{character_name}.png").exists():
            char_png = lib / f"{character_name}.png"
    voice = voice or character.get("tts_voice") or DEFAULT_VOICE

    hero_seconds = 6
    led = estimate(
        lines,
        heroes,
        hero_seconds,
        tier,
        image_model,
        "file" if source_file else research,
        with_music=with_music,
    )
    console.print("[bold]Cost estimate[/bold]")
    for ln in led.lines():
        console.print("  " + ln)
    if budget is not None and led.total > budget:
        console.print(
            f"[red]Estimate ${led.total:.2f} is over the --budget ${budget:.2f}. Lower --heroes or --lines, or use --tier lite.[/red]"
        )
        return None
    if dry_run:
        return None

    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out = resume_dir or settings.output_base_dir / f"Hybrid_{slug(topic)}_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    console.print(f"Output: [yellow]{out}[/yellow]")

    # 1. Source material
    src_path = out / "source.md"
    if not media.exists(src_path):
        if source_file:
            src_path.write_text(Path(source_file).read_text())
        elif research == "deep":
            media.run(
                [settings.deep_research_cmd, "research", topic, "--output", src_path]
            )
        elif research == "quick":
            console.print("[cyan]Researching (Gemini + Google Search)...[/cyan]")
            src_path.write_text(quick_research(topic))
        else:
            src_path.write_text(topic)

    # 2. Plan
    plan_path = out / "plan.json"
    plan = media.load_json(plan_path)
    if not plan:
        console.print("[cyan]Writing the script...[/cyan]")
        plan = plan_script(src_path.read_text(), character, lines, heroes, aspect)
        media.save_json(plan, plan_path)
    assert isinstance(plan, list)
    (out / "script.txt").write_text("\n".join(s["line"] for s in plan))

    # 3. Narration, one voice for the whole piece
    style = out / "voice_style.md"
    style.write_text(
        "### AUDIO PROFILE\n"
        + character.get("voice_prompt", "")
        + "\n### DIRECTOR NOTES\nConversational pace, smile in the voice, crisp consonants. Read only the transcript.\n"
    )
    console.print(
        f"[cyan]Recording narration ({len(plan)} lines, voice {voice})...[/cyan]"
    )
    wavs = [
        media.tts(s["line"], out / f"line_{i:02}.wav", voice, style)
        for i, s in enumerate(plan)
    ]
    voice_wav = out / "narration.wav"
    slots = media.concat_audio(wavs, 0.35, voice_wav)

    # 4. Visuals
    neg = "text, captions, watermark, logo, extra limbs, deformed"
    clips: list[Path] = []
    model_id = costs.IMAGE_MODELS[image_model][0]
    for i, (s, slot) in enumerate(zip(plan, slots)):
        console.print(
            f"[cyan]Scene {i + 1}/{len(plan)} ({'hero' if s['hero'] else s['shot']})...[/cyan]"
        )
        refs = [char_png] if (char_png and s["shot"] == "presenter") else []
        prompt = s["visual"]
        if s["shot"] == "presenter" and char_png:
            prompt = f"The same character as the reference image, identical look and outfit. {prompt}"
        img = media.image(
            prompt,
            out / f"scene_{i:02}.png",
            aspect,
            model_id,
            refs=[r for r in refs if r],
            negative=neg,
        )
        clip = out / f"clip_{i:02}.mp4"
        if s["hero"]:
            secs = costs.hero_duration(slot)
            motion = (
                "gentle natural motion, subtle camera push-in"
                if s["shot"] == "broll"
                else "the character gestures and talks expressively, natural small movements, steady camera"
            )
            raw = media.veo(
                f"{s['visual']}. {motion}",
                img,
                out / f"hero_{i:02}.mp4",
                aspect,
                secs,
                tier,
            )
            media.fit_clip(raw, slot, clip, aspect)
        else:
            media.still_clip(img, slot, clip, aspect, i)
        clips.append(clip)

    # 5. Music, captions, final mix
    mus = (
        media.music(
            f"Light, warm background bed for a short video about {topic}; unobtrusive, loopable, no vocals",
            out / "music.mp3",
        )
        if with_music
        else None
    )
    subs = (
        media.srt([caption_text(s["line"]) for s in plan], slots, out / "captions.srt")
        if captions
        else None
    )
    final = out / f"Mirage_{slug(topic, 40)}.mp4"
    console.print("[cyan]Mixing and encoding...[/cyan]")
    media.assemble(clips, voice_wav, final, mus, subs, aspect)

    led.write(out / "cost_estimate.json")
    console.print(
        f"[bold green]Done:[/bold green] {final}  (estimated ${led.total:.2f})"
    )
    return final
