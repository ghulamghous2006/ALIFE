"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    """Immutable application configuration."""

    env: str
    log_level: str


def load_config() -> Config:
    """Load configuration from environment variables and optional .env file.

    Returns:
        Parsed application configuration.
    """
    load_dotenv()

    return Config(
        env=os.getenv("ALIFE_ENV", "development"),
        log_level=os.getenv("ALIFE_LOG_LEVEL", "INFO"),
    )
