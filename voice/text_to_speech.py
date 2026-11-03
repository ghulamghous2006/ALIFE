"""Offline text-to-speech playback for ALIFE."""

import logging

import pyttsx3

from voice.exceptions import TextToSpeechError

logger = logging.getLogger(__name__)

DEFAULT_SPEECH_RATE = 180


class TextToSpeech:
    """Convert ALIFE response text into spoken audio."""

    def __init__(self, speech_rate: int = DEFAULT_SPEECH_RATE) -> None:
        """Initialize the text-to-speech engine."""
        self._speech_rate = speech_rate
        self._engine = None

    def _get_engine(self):
        """Lazy-load the pyttsx3 engine."""
        if self._engine is None:
            try:
                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", self._speech_rate)
            except Exception as exc:
                raise TextToSpeechError(f"Failed to initialize text-to-speech: {exc}") from exc
        return self._engine

    def speak(self, text: str) -> None:
        """Speak the provided text through the default speakers.

        Args:
            text: Text to speak aloud.

        Raises:
            TextToSpeechError: If speech playback fails.
        """
        if not text.strip():
            logger.warning("Empty text received for speech playback")
            return

        try:
            engine = self._get_engine()
            engine.say(text)
            engine.runAndWait()
            logger.info("Spoke response (%d characters)", len(text))
        except Exception as exc:
            logger.error("Text-to-speech failed: %s", exc)
            raise TextToSpeechError(f"Text-to-speech failed: {exc}") from exc
