from pathlib import Path
from mirage.config import Settings


def test_default_settings():
    # Load settings ignoring any local .env file to test defaults
    clean_settings = Settings(_env_file=None)

    assert clean_settings.default_location == "home"
    assert clean_settings.atmos_cmd == "atmos"
    assert clean_settings.output_base_dir == Path.home() / "Documents" / "Mirage"
    assert clean_settings.log_file == Path.home() / ".config" / "mirage" / "mirage.log"
