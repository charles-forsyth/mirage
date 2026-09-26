"""Price table and a small cost ledger for Mirage runs.

Prices are Gemini API paid-tier list prices (USD), checked 2026-09-26 against
https://ai.google.dev/gemini-api/docs/pricing and the project's billing export.
They are estimates for planning; the billing export is the source of truth.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Veo 3.1 video with audio, per second at 720p.
VEO_PER_SECOND = {"lite": 0.05, "fast": 0.10, "standard": 0.40}

# Image generation, per image at 1K (Nano Banana 2) or 1K/2K (Nano Banana Pro).
IMAGE_MODELS = {
    "flash": ("gemini-3.1-flash-image", 0.067),  # Nano Banana 2
    "pro": ("gemini-3-pro-image", 0.134),  # Nano Banana Pro
}

# Gemini Flash TTS: $20 per 1M audio tokens at 25 tokens/s of audio.
TTS_PER_SECOND = 20.0 / 1_000_000 * 25

# Lyria: a <=30 s clip vs a full-length track (per request, from billing export).
MUSIC_CLIP = 0.04
MUSIC_FULL = 0.08

# Text work (rough per-call figures at current Flash/Pro token prices).
PLANNER_CALL = 0.02
QUICK_RESEARCH = 0.03  # Flash + Google Search grounding (5,000 free searches/month)
DEEP_RESEARCH = 2.00  # Google's estimate for the Deep Research agent: $1-3 per task

WORDS_PER_SECOND = 2.6  # narration pace used for estimates before TTS runs


@dataclass
class Ledger:
    """Tracks estimated spend by line item."""

    items: list[dict] = field(default_factory=list)

    def add(self, item: str, qty: float, unit_price: float, note: str = "") -> None:
        self.items.append(
            {
                "item": item,
                "qty": round(qty, 2),
                "unit_price": unit_price,
                "cost": round(qty * unit_price, 4),
                "note": note,
            }
        )

    @property
    def total(self) -> float:
        return round(sum(i["cost"] for i in self.items), 2)

    def lines(self) -> list[str]:
        out = [
            f"{i['item']:<34} {i['qty']:>7} x ${i['unit_price']:<7} = ${i['cost']:.2f}"
            for i in self.items
        ]
        out.append(f"{'TOTAL (estimate)':<34} {'':>7}   {'':<8}  ${self.total:.2f}")
        return out

    def write(self, path: Path) -> None:
        path.write_text(
            json.dumps({"items": self.items, "total_usd": self.total}, indent=2)
        )


def hero_duration(speech_seconds: float) -> int:
    """Shortest Veo clip length (4/6/8 s) that covers the line, capped at 8."""
    for d in (4, 6, 8):
        if speech_seconds <= d:
            return d
    return 8
