"""Low-cost media helpers: safe subprocess calls, caching, and ffmpeg assembly.

Every external tool is called with an argument list (never a shell string), so
quotes and apostrophes in topics or scripts cannot break or inject commands.
Every generator skips work when its output already exists, so a failed run can
be resumed without paying twice.
"""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any, Optional, Sequence

from rich.console import Console

from mirage.config import settings

console = Console()


def run(
    args: Sequence[Any],
    quiet: bool = True,
    env: Optional[dict] = None,
    stdin: Optional[str] = None,
) -> str:
    """Run a command as an argument list. Raises CalledProcessError with stderr shown."""
    try:
        r = subprocess.run(
            [str(a) for a in args],
            check=True,
            capture_output=True,
            text=True,
            env=env,
            input=stdin,
        )
        if not quiet and r.stdout:
            console.print(r.stdout)
        return r.stdout
    except subprocess.CalledProcessError as e:
        console.print(
            f"[bold red]Command failed:[/bold red] {' '.join(map(str, args))[:300]}"
        )
        tail = (e.stderr or e.stdout or "").strip().splitlines()[-8:]
        for line in tail:
            console.print(f"  [red]{line}[/red]")
        raise


def exists(p: Path) -> bool:
    return p.exists() and p.stat().st_size > 0


def duration(p: Path) -> float:
    out = run(
        [
            settings.ffprobe_cmd,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(p),
        ]
    )
    return float(out.strip())


# ---------- generators (all cached) ----------


def expected_speech_seconds(text: str) -> float:
    return max(1.5, len(text.split()) / 2.6)


def tts(text: str, out_wav: Path, voice: str, style_file: Optional[Path]) -> Path:
    """One narration line. The voice character comes from the prebuilt voice; a style file is
    not sent because gen-tts appends the transcript to it and the model then reads the line
    twice. A result much longer than the words need is treated as a repeat and regenerated."""
    if exists(out_wav):
        return out_wav
    args = [
        settings.gen_tts_cmd,
        text,
        "--voice-name",
        voice,
        "--no-play",
        "--audio-format",
        "WAV",
        "--output-file",
        out_wav,
    ]
    limit = expected_speech_seconds(text) * 1.9 + 1.5
    for attempt in range(3):
        run_retry(args)
        if duration(out_wav) <= limit:
            return out_wav
        console.print(
            f"[yellow]Narration line ran {duration(out_wav):.1f}s (expected under {limit:.1f}s); regenerating[/yellow]"
        )
        out_wav.unlink()
    run_retry(args)
    return out_wav


def image(
    prompt: str,
    out_png: Path,
    aspect: str,
    model: str,
    refs: Sequence[Path] = (),
    negative: str = "",
) -> Path:
    if exists(out_png):
        return out_png
    args = [
        settings.lumina_cmd,
        "-p",
        prompt,
        "--model-name",
        model,
        "--image-size",
        "1K",
        "--aspect-ratio",
        aspect,
        "--output-dir",
        out_png.parent,
        "-f",
        out_png.name,
    ]
    for r in refs:
        args += ["-i", r]
    if negative:
        args += ["--negative-prompt", negative]
    run_retry(args)
    return out_png


TRANSIENT = (
    "503",
    "UNAVAILABLE",
    "429",
    "RESOURCE_EXHAUSTED",
    "500 INTERNAL",
    "DEADLINE_EXCEEDED",
)


def run_retry(args: Sequence[Any], attempts: int = 3, wait: float = 20.0) -> str:
    """Run a generator call, retrying transient API errors (503/429/500) with backoff."""
    import time

    for n in range(1, attempts + 1):
        try:
            return run(args)
        except subprocess.CalledProcessError as e:
            text = f"{e.stdout or ''}{e.stderr or ''}"
            if n == attempts or not any(k in text for k in TRANSIENT):
                raise
            console.print(
                f"[yellow]Transient API error, retry {n}/{attempts - 1} in {wait * n:.0f}s[/yellow]"
            )
            time.sleep(wait * n)
    return ""


def veo(
    prompt: str,
    image_path: Path,
    out_mp4: Path,
    aspect: str,
    seconds: int,
    tier: str,
    audio: bool = False,
) -> Path:
    if exists(out_mp4):
        return out_mp4
    args = [
        settings.vidius_cmd,
        prompt,
        "-i",
        image_path,
        "-o",
        out_mp4,
        "-ar",
        aspect,
        "-d",
        str(seconds),
        "-m",
        tier,
    ]
    if not audio:
        args.append("-na")
    run_retry(args)
    return out_mp4


def music(prompt: str, out_mp3: Path, seconds: int = 30) -> Path:
    if exists(out_mp3):
        return out_mp3
    run_retry(
        [settings.gen_music_cmd, prompt, "-o", out_mp3, "-f", "mp3", "-d", str(seconds)]
    )
    return out_mp3


# ---------- ffmpeg assembly ----------


def dims(aspect: str) -> tuple[int, int]:
    return (720, 1280) if aspect == "9:16" else (1280, 720)


def still_clip(
    img: Path,
    seconds: float,
    out_mp4: Path,
    aspect: str,
    variant: int,
    gentle: bool = False,
) -> Path:
    """Ken Burns clip: slow zoom in or out with a gentle drift. No API cost."""
    if exists(out_mp4):
        return out_mp4
    w, h = dims(aspect)
    fps = 30
    frames = max(1, math.ceil(seconds * fps))
    zoom_in = variant % 2 == 0
    rate, peak = (0.00015, 1.03) if gentle else (0.0009, 1.15)
    z = f"min(1+{rate}*on,{peak})" if zoom_in else f"max({peak}-{rate}*on,1.0)"
    drifts = [
        "iw/2-(iw/zoom/2)",
        "iw/2-(iw/zoom/2)+on*0.15",
        "iw/2-(iw/zoom/2)-on*0.15",
    ]
    dx = drifts[0] if gentle else drifts[variant % 3]
    vf = (
        f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
        f"zoompan=z='{z}':x='{dx}':y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps={fps},"
        f"format=yuv420p"
    )
    run(
        [
            settings.ffmpeg_cmd,
            "-y",
            "-loop",
            "1",
            "-i",
            img,
            "-vf",
            vf,
            "-t",
            f"{seconds:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-an",
            out_mp4,
        ]
    )
    return out_mp4


def fit_clip(src: Path, seconds: float, out_mp4: Path, aspect: str) -> Path:
    """Trim or hold-extend a Veo clip to exactly `seconds`, scaled to the frame, audio dropped."""
    if exists(out_mp4):
        return out_mp4
    w, h = dims(aspect)
    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
        f"tpad=stop_mode=clone:stop_duration=10,fps=30,format=yuv420p"
    )
    run(
        [
            settings.ffmpeg_cmd,
            "-y",
            "-i",
            src,
            "-vf",
            vf,
            "-t",
            f"{seconds:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-an",
            out_mp4,
        ]
    )
    return out_mp4


def loop_clip(src: Path, seconds: float, out_mp4: Path, aspect: str) -> Path:
    """Fit a talking clip to `seconds`; if the line runs longer than the clip, loop it so the
    character keeps moving instead of freezing on the last frame."""
    if exists(out_mp4):
        return out_mp4
    w, h = dims(aspect)
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps=30,format=yuv420p"
    run(
        [
            settings.ffmpeg_cmd,
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            src,
            "-vf",
            vf,
            "-t",
            f"{seconds:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-an",
            out_mp4,
        ]
    )
    return out_mp4


def concat_audio(wavs: Sequence[Path], gap: float, out_wav: Path) -> list[float]:
    """Join narration lines with a short pause; returns each line's slot length (speech + gap)."""
    slots = [duration(w) + gap for w in wavs]
    lst = out_wav.with_suffix(".txt")
    silence = out_wav.parent / "_gap.wav"
    run(
        [
            settings.ffmpeg_cmd,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=24000:cl=mono",
            "-t",
            str(gap),
            silence,
        ]
    )
    with open(lst, "w") as f:
        for wv in wavs:
            f.write(f"file '{wv.resolve()}'\nfile '{silence.resolve()}'\n")
    run(
        [
            settings.ffmpeg_cmd,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            lst,
            "-c:a",
            "pcm_s16le",
            out_wav,
        ]
    )
    return slots


def srt(lines: Sequence[str], slots: Sequence[float], out_srt: Path) -> Path:
    def ts(t: float) -> str:
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"

    t = 0.0
    with open(out_srt, "w") as f:
        for i, (line, s) in enumerate(zip(lines, slots), 1):
            f.write(f"{i}\n{ts(t)} --> {ts(t + s - 0.15)}\n{line}\n\n")
            t += s
    return out_srt


def assemble(
    clips: Sequence[Path],
    voice_wav: Path,
    out_mp4: Path,
    music_mp3: Optional[Path] = None,
    subtitles: Optional[Path] = None,
    aspect: str = "9:16",
) -> Path:
    """Concat silent clips, lay narration on top, duck music under it, burn captions, encode small."""
    work = out_mp4.parent
    lst = work / "_clips.txt"
    with open(lst, "w") as f:
        for c in clips:
            f.write(f"file '{c.resolve()}'\n")
    silent = work / "_silent.mp4"
    run(
        [
            settings.ffmpeg_cmd,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            lst,
            "-c",
            "copy",
            silent,
        ]
    )

    args = [settings.ffmpeg_cmd, "-y", "-i", silent, "-i", voice_wav]
    vf = "null"
    if subtitles:
        size = 13 if aspect == "9:16" else 18
        style = f"FontName=DejaVu Sans,FontSize={size},Outline=2,Shadow=0,MarginV={60 if aspect == '9:16' else 30}"
        vf = f"subtitles={subtitles.resolve()}:force_style='{style}'"
    if music_mp3:
        args += ["-stream_loop", "-1", "-i", music_mp3]
        af = (
            "[1:a]aresample=48000,aformat=channel_layouts=stereo,asplit=2[v1][v2];"
            "[2:a]aresample=48000,aformat=channel_layouts=stereo,volume=0.35[m];"
            "[m][v1]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[md];"
            "[v2][md]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5[a]"
        )
    else:
        af = "[1:a]aresample=48000,loudnorm=I=-16:TP=-1.5[a]"
    args += [
        "-filter_complex",
        f"[0:v]{vf}[v];{af}",
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-shortest",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "24",
        "-maxrate",
        "4M",
        "-bufsize",
        "8M",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        out_mp4,
    ]
    run(args)
    return out_mp4


def save_json(obj: object, path: Path) -> None:
    path.write_text(json.dumps(obj, indent=2))


def load_json(path: Path) -> Optional[object]:
    return json.loads(path.read_text()) if exists(path) else None
