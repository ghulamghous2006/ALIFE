"""Voice interaction coordinator for ALIFE."""

import logging
from dataclasses import dataclass

from brain.conversation.conversation_manager import ConversationManager
from voice.audio_recorder import AudioRecorder
from voice.exceptions import TextToSpeechError, VoiceError
from voice.speech_to_text import SpeechToText
from voice.text_to_speech import TextToSpeech

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VoiceInteractionResult:
    """Result of a voice interaction cycle."""

    heard: str
    response: str


class VoiceManager:
    """Coordinates recording, transcription, conversation, and speech output."""

    def __init__(
        self,
        conversation: ConversationManager,
        recorder: AudioRecorder | None = None,
        speech_to_text: SpeechToText | None = None,
        text_to_speech: TextToSpeech | None = None,
    ) -> None:
        """Initialize the voice manager."""
        self._conversation = conversation
        self._recorder = recorder or AudioRecorder()
        self._speech_to_text = speech_to_text or SpeechToText()
        self._text_to_speech = text_to_speech or TextToSpeech()

    def listen_and_respond(self) -> VoiceInteractionResult:
        """Record speech, process it through ALIFE, and speak the response.

        Returns:
            Heard transcript and ALIFE response text.
        """
        try:
            audio = self._recorder.record()
            heard = self._speech_to_text.transcribe(audio)
        except VoiceError as exc:
            logger.error("Voice capture failed: %s", exc)
            return VoiceInteractionResult(
                heard="",
                response=f"Voice interaction failed: {exc}",
            )

        if not heard.strip():
            response = "I didn't catch anything. Please try again."
            logger.warning("No speech detected during voice interaction")
            return VoiceInteractionResult(heard="", response=response)

        logger.info("Voice transcript: %s", heard)
        try:
            response = self._conversation.generate_response(heard)
        except Exception as exc:
            logger.exception("Conversation pipeline failed for voice input: %s", exc)
            return VoiceInteractionResult(
                heard=heard,
                response=f"I heard you, but I couldn't complete the request: {exc}",
            )

        try:
            self._text_to_speech.speak(response)
        except TextToSpeechError as exc:
            logger.error("Spoken response failed: %s", exc)
            response = f"{response}\n(I generated a reply, but speech playback failed.)"

        return VoiceInteractionResult(heard=heard, response=response)
