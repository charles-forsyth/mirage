from pathlib import Path
from mirage.config import Settings


def test_default_settings():
    # Load settings ignoring any local .env file to test defaults
    clean_settings = Settings(_env_file=None)

    assert clean_settings.default_location == "home"
    assert clean_settings.atmos_cmd == "atmos"
    assert clean_settings.output_base_dir == Path.home() / "Documents" / "Mirage"
    assert clean_settings.log_file == Path.home() / ".config" / "mirage" / "mirage.log"


def test_planner_uses_header_key_and_current_model(tmp_path, monkeypatch):
    from unittest.mock import MagicMock, patch

    from mirage import planner

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr(
        planner.os.path, "expanduser", lambda p: str(tmp_path / "missing.env")
    )
    fake = MagicMock()
    fake.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": '[{"narration": "a", "visual_prompt": "b"}]'}]
                }
            }
        ]
    }
    with patch("mirage.planner.requests.post", return_value=fake) as post:
        plan = planner.generate_news_plan("a")
    assert plan == [{"narration": "a", "visual_prompt": "b"}]
    url = post.call_args.args[0]
    assert "key=" not in url and planner.PLANNER_MODEL in url
    assert post.call_args.kwargs["headers"]["x-goog-api-key"] == "fake-key"
    assert (
        "preview" not in planner.PLANNER_MODEL
        or planner.PLANNER_MODEL == "gemini-3.1-pro-preview"
    )
