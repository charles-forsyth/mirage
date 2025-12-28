from pathlib import Path
from mirage.config import settings

def test_default_settings():
    assert settings.default_location == "home"
    assert settings.atmos_cmd == "atmos"
    assert settings.output_base_dir == Path.home() / "Documents" / "Mirage"
    assert settings.log_file == Path.home() / ".config" / "mirage" / "mirage.log"