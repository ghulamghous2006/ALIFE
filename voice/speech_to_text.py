
"""Offline speech-to-text using faster-whisper."""

import logging
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

from voice.exceptions import SpeechRecognitionError

logger = logging.getLogger(__name__)

DEFAULT_MODEL_SIZE = "tiny"


class SpeechToText:
    """Convert microphone audio into text using faster-whisper."""

    def __init__(self, model_size: str = DEFAULT_MODEL_SIZE) -> None:
        """Initialize the speech-to-text component."""
        self._model_size = model_size
        self._model: Optional[WhisperModel] = None

    def _load_model(self) -> WhisperModel:
        """Lazy-load the Whisper model on first use and reuse it afterwards."""
        if self._model is None:
            logger.info(
                "Loading faster-whisper model=%s on cpu",
                self._model_size,
            )
            self._model = WhisperModel(
                self._model_size,
                device="cpu",
                compute_type="int8",
            )
        return self._model

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16_000) -> str:
        """Transcribe audio samples into text.

        Args:
            audio: Audio samples recorded from the microphone.
            sample_rate: Sample rate of the audio input.

        Returns:
            Recognized text, or an empty string if nothing was detected.

        Raises:
            SpeechRecognitionError: If transcription fails.
        """
        if audio.size == 0:
            logger.warning("Empty audio received for transcription")
            return ""

        try:
            samples = np.asarray(audio, dtype=np.float32).reshape(-1)

            if not np.all(np.isfinite(samples)):
                raise SpeechRecognitionError(
                    "Audio contains invalid samples."
                )

            model = self._load_model()

            segments, info = model.transcribe(
                samples,
                language="en",
                beam_size=5,
                vad_filter=True,
                condition_on_previous_text=False,
            )

            parts: list[str] = []
            for segment in segments:
                text = segment.text.strip()
                if text:
                    parts.append(text)

            result = " ".join(parts).strip()

            logger.info(
                "Speech recognized (%d characters, language=%s)",
                len(result),
                getattr(info, "language", "unknown"),
            )

            if not result:
                logger.warning(
                    "No speech recognized. Try speaking clearly and closer "
                    "to the microphone."
                )

            return result

        except SpeechRecognitionError:
            raise
        except Exception as exc:
            logger.error("Speech recognition failed: %s", exc)
            raise SpeechRecognitionError(
                f"Speech recognition failed: {exc}"
            ) from exc
