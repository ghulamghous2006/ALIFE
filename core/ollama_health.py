"""Ollama availability checks used at application startup."""

import logging
import time

import httpx

logger = logging.getLogger(__name__)

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_ATTEMPTS = 6
DEFAULT_DELAY_SECONDS = 2.0


def wait_for_ollama(
    host: str = DEFAULT_HOST,
    attempts: int = DEFAULT_ATTEMPTS,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
) -> bool:
    """Wait briefly for the local Ollama server to become reachable.

    Args:
        host: Ollama base URL.
        attempts: Number of connection attempts.
        delay_seconds: Delay between attempts.

    Returns:
        True if Ollama responded, otherwise False.
    """
    url = host.rstrip("/") + "/api/tags"
    for attempt in range(1, attempts + 1):
        try:
            response = httpx.get(url, timeout=2.0)
            if response.status_code < 500:
                logger.info("Ollama is reachable at %s", host)
                return True
        except httpx.HTTPError as exc:
            logger.warning(
                "Ollama not ready (attempt %s/%s): %s",
                attempt,
                attempts,
                exc,
            )
        time.sleep(delay_seconds)

    logger.error("Ollama did not become ready at %s", host)
    return False
