from mirage.config import settings

def test_default_settings():
    assert settings.default_location == "home"
    assert settings.atmos_cmd == "atmos"
