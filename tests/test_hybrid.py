"""Tests for the hybrid pipeline's cost logic, planning guardrails and safe commands."""

from pathlib import Path
from unittest.mock import patch

from mirage import costs, hybrid, media


def test_hero_duration_picks_shortest_veo_length():
    assert costs.hero_duration(3.1) == 4
    assert costs.hero_duration(5.9) == 6
    assert costs.hero_duration(7.5) == 8
    assert costs.hero_duration(12) == 8


def test_estimate_default_is_cheap_and_video_is_bounded():
    led = hybrid.estimate(16, 3, 6, "lite", "flash", "quick")
    assert led.total < 3.0
    veo = [i for i in led.items if i["item"].startswith("Veo")]
    assert veo and veo[0]["qty"] == 18 and veo[0]["unit_price"] == 0.05


def test_estimate_stills_only_has_no_video():
    led = hybrid.estimate(16, 0, 6, "lite", "flash", "none")
    assert not [i for i in led.items if i["item"].startswith("Veo")]


def test_plan_enforces_hero_budget_and_opening_hero():
    fake = [
        {
            "line": f"l{i}",
            "shot": "presenter" if i % 3 == 0 else "weird",
            "hero": True,
            "visual": "v",
        }
        for i in range(10)
    ]
    with patch.object(hybrid, "_gemini_json", return_value=fake):
        plan = hybrid.plan_script("src", {}, 10, 3, "9:16")
    assert sum(s["hero"] for s in plan) == 3
    assert plan[0]["hero"] is True
    assert {s["shot"] for s in plan} <= {"presenter", "broll"}


def test_budget_guard_stops_before_spending(tmp_path):
    with (
        patch.object(hybrid, "quick_research") as qr,
        patch.object(media, "run") as run,
    ):
        out = hybrid.build(
            "topic",
            None,
            research="quick",
            heroes=20,
            lines=20,
            tier="standard",
            budget=1.0,
        )
    assert out is None
    qr.assert_not_called()
    run.assert_not_called()


def test_run_uses_argument_list_so_quotes_are_safe():
    with patch("mirage.media.subprocess.run") as sr:
        sr.return_value.stdout = ""
        media.run(["echo", 'it\'s "quoted"; rm -rf /', Path("/tmp/x")])
    args, kwargs = sr.call_args
    assert args[0] == ["echo", 'it\'s "quoted"; rm -rf /', "/tmp/x"]
    assert "shell" not in kwargs


def test_generators_skip_existing_outputs(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(b"x")
    with patch.object(media, "run") as run:
        media.image("prompt", p, "9:16", "gemini-3.1-flash-image")
        media.veo("prompt", p, p, "9:16", 4, "lite")
    run.assert_not_called()


def test_caption_text_undoes_tts_spellings():
    assert (
        hybrid.caption_text("massive A-I news from Open-A-I and x-A-I")
        == "massive AI news from OpenAI and xAI"
    )
    assert (
        hybrid.caption_text("four T-P-Us and the R-T-X card")
        == "four TPUs and the RTX card"
    )
