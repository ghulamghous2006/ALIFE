"""Push-to-talk microphone recording for ALIFE."""

import logging

import numpy as np
import sounddevice as sd

from voice.exceptions import AudioRecordingError

logger = logging.getLogger(__name__)

DEFAULT_SAMPLE_RATE = 16_000
DEFAULT_CHANNELS = 1
DEFAULT_DURATION_SECONDS = 6.0


class AudioRecorder:
    """Records microphone audio for offline speech recognition."""

    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        channels: int = DEFAULT_CHANNELS,
        duration_seconds: float = DEFAULT_DURATION_SECONDS,
    ) -> None:
        """Initialize the audio recorder."""
        self._sample_rate = sample_rate
        self._channels = channels
        self._duration_seconds = duration_seconds

    @property
    def sample_rate(self) -> int:
        """Return the configured sample rate."""
        return self._sample_rate

    def record(self) -> np.ndarray:
        """Record a fixed-duration audio clip from the default microphone.

        Returns:
            One-dimensional audio samples as a float32 numpy array.

        Raises:
            AudioRecordingError: If recording fails.
        """
        logger.info(
            "Recording audio for %.1f seconds at %s Hz",
            self._duration_seconds,
            self._sample_rate,
        )
        try:
            audio = sd.rec(
                int(self._duration_seconds * self._sample_rate),
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="float32",
            )
            sd.wait()
            samples = np.asarray(audio, dtype=np.float32)
            if samples.ndim > 1:
                samples = np.mean(samples, axis=1)
            samples = np.squeeze(samples)
            samples = samples - np.mean(samples)
            peak = np.max(np.abs(samples)) if samples.size else 0.0
            if peak > 0:
                samples = samples / peak
            logger.info("Recorded %s audio samples (peak=%.4f)", samples.size, float(peak))
            if peak < 0.001:
                logger.warning("Recorded audio is very quiet; transcription may be empty")
            return samples.astype(np.float32)
        except Exception as exc:
            logger.error("Microphone recording failed: %s", exc)
            raise AudioRecordingError(f"Microphone recording failed: {exc}") from exc
