"""Ollama LLM provider for local model inference."""

import logging
from pathlib import Path
from typing import Optional

import httpx
from ollama import Client, ResponseError

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "qwen3:4b"
DEFAULT_HOST = "http://localhost:11434"

FALLBACK_SYSTEM_PROMPT = (
    "You are ALIFE, a helpful AI assistant."
)


class OllamaProviderError(Exception):
    """Base exception for Ollama provider failures."""


class OllamaConnectionError(OllamaProviderError):
    """Raised when the Ollama server cannot be reached."""


class OllamaProvider:
    """Provider for generating text via a local Ollama model."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        host: str = DEFAULT_HOST,
        client: Optional[Client] = None,
    ) -> None:
        """
        Initialize the Ollama provider.

        Args:
            model: Ollama model identifier.
            host: Base URL of the Ollama server.
            client: Optional client instance for testing.
        """

        self._model = model
        self._host = host
        self._client = client or Client(host=host)

        self.system_prompt = self._load_system_prompt()

    @property
    def model(self) -> str:
        """Return the configured model name."""
        return self._model

    def _load_system_prompt(self) -> str:
        """
        Load the ALIFE system prompt from disk.

        Returns:
            System prompt string.
        """

        prompt_path = (
            Path(__file__).resolve().parent.parent / "prompts" / "system_prompt.txt"
        )

        try:
            prompt = prompt_path.read_text(
                encoding="utf-8"
            ).strip()

            logger.info(
                "Loaded system prompt from %s",
                prompt_path,
            )

            return prompt

        except FileNotFoundError:
            logger.error(
                "System prompt not found at %s. Using fallback prompt.",
                prompt_path,
            )

            return FALLBACK_SYSTEM_PROMPT

        except Exception as exc:
            logger.exception(
                "Failed to load system prompt: %s",
                exc,
            )

            return FALLBACK_SYSTEM_PROMPT

    def generate(self, prompt: str) -> str:
        """
        Send a prompt to the Ollama model and return the generated response.

        Args:
            prompt: User message.

        Returns:
            AI response.

        Raises:
            ValueError
            OllamaConnectionError
            OllamaProviderError
        """

        if not prompt.strip():
            raise ValueError("Prompt must not be empty.")

        logger.info(
            "Generating response with model=%s",
            self._model,
        )

        full_prompt = f"""
{self.system_prompt}

User:
{prompt}

ALIFE:
""".strip()

        try:

            response = self._client.generate(
                model=self._model,
                prompt=full_prompt,
            )

        except (httpx.ConnectError, httpx.TimeoutException) as exc:

            logger.error(
                "Failed to connect to Ollama at %s: %s",
                self._host,
                exc,
            )

            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self._host}. "
                "Ensure Ollama is installed and running."
            ) from exc

        except ResponseError as exc:

            logger.error(
                "Ollama API error (status=%s): %s",
                exc.status_code,
                exc.error,
            )

            raise OllamaProviderError(
                f"Ollama request failed: {exc.error}"
            ) from exc

        except httpx.RequestError as exc:

            logger.error(
                "Network error communicating with Ollama: %s",
                exc,
            )

            raise OllamaConnectionError(
                f"Network error communicating with Ollama: {exc}"
            ) from exc

        text = (response.response or "").strip()
        if not text:
            logger.warning("Ollama returned an empty response for model=%s", self._model)
            raise OllamaProviderError("Ollama returned an empty response.")

        logger.info(
            "Generation complete (%d characters)",
            len(text),
        )

        return text
