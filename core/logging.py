"""Centralized logging configuration."""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger for the application.

    Args:
        level: Logging level name (e.g. DEBUG, INFO, WARNING).
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
