from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Configuration settings for Mirage."""
    
    # External Tool Commands (can be overridden via env vars or .env file)
    atmos_cmd: str = "atmos"
    gen_tts_cmd: str = "gen-tts"
    lumina_cmd: str = "lumina"
    vidius_cmd: str = "vidius"
    convert_cmd: str = "convert"
    deep_research_cmd: str = "deep-research"
    gen_music_cmd: str = "gen-music"
    ffmpeg_cmd: str = "ffmpeg"
    ffprobe_cmd: str = "ffprobe"
    
    # Default Location
    default_location: str = "home"

    # Paths
    output_base_dir: Path = Path.home() / "Documents" / "Mirage"
    log_file: Path = Path.home() / ".config" / "mirage" / "mirage.log"
    character_library_dir: Path = Path.home() / ".config" / "mirage" / "characters"

    model_config = SettingsConfigDict(
        env_file=str(Path.home() / ".config" / "mirage" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()