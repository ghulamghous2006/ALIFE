"""Custom exceptions for the ALIFE voice system."""


class VoiceError(Exception):
    """Base exception for voice-related failures."""


class SpeechRecognitionError(VoiceError):
    """Raised when speech recognition fails."""


class AudioRecordingError(VoiceError):
    """Raised when microphone recording fails."""


class TextToSpeechError(VoiceError):
    """Raised when text-to-speech playback fails."""
