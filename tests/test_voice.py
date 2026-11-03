"""Tests for the ALIFE voice manager."""

import unittest
from unittest.mock import MagicMock

import numpy as np

from voice.audio_recorder import AudioRecorder
from voice.exceptions import SpeechRecognitionError, TextToSpeechError
from voice.speech_to_text import SpeechToText
from voice.voice_manager import VoiceManager


class TestVoiceManager(unittest.TestCase):
    """Unit tests for voice interaction flow."""

    def test_empty_speech_handling(self) -> None:
        conversation = MagicMock()
        recorder = MagicMock()
        recorder.record.return_value = np.zeros(16000, dtype="float32")
        speech_to_text = MagicMock()
        speech_to_text.transcribe.return_value = ""
        text_to_speech = MagicMock()

        manager = VoiceManager(
            conversation=conversation,
            recorder=recorder,
            speech_to_text=speech_to_text,
            text_to_speech=text_to_speech,
        )

        result = manager.listen_and_respond()

        self.assertEqual(result.heard, "")
        self.assertIn("didn't catch", result.response.lower())
        conversation.generate_response.assert_not_called()
        text_to_speech.speak.assert_not_called()

    def test_voice_pipeline_uses_existing_conversation(self) -> None:
        conversation = MagicMock()
        conversation.generate_response.return_value = "Java is a programming language."
        recorder = MagicMock()
        recorder.record.return_value = np.ones(16000, dtype="float32")
        speech_to_text = MagicMock()
        speech_to_text.transcribe.return_value = "What is Java?"
        text_to_speech = MagicMock()

        manager = VoiceManager(
            conversation=conversation,
            recorder=recorder,
            speech_to_text=speech_to_text,
            text_to_speech=text_to_speech,
        )

        result = manager.listen_and_respond()

        conversation.generate_response.assert_called_once_with("What is Java?")
        text_to_speech.speak.assert_called_once_with("Java is a programming language.")
        self.assertEqual(result.response, "Java is a programming language.")

    def test_transcribed_tool_request_uses_shared_pipeline(self) -> None:
        conversation = MagicMock()
        conversation.generate_response.return_value = "Done. I've opened Youtube."
        recorder = MagicMock()
        recorder.record.return_value = np.ones(16000, dtype="float32")
        speech_to_text = MagicMock()
        speech_to_text.transcribe.return_value = "open YouTube"
        text_to_speech = MagicMock()

        manager = VoiceManager(
            conversation=conversation,
            recorder=recorder,
            speech_to_text=speech_to_text,
            text_to_speech=text_to_speech,
        )

        result = manager.listen_and_respond()

        conversation.generate_response.assert_called_once_with("open YouTube")
        self.assertIn("opened", result.response.lower())

    def test_transcription_failure_does_not_crash(self) -> None:
        conversation = MagicMock()
        recorder = MagicMock()
        recorder.record.return_value = np.ones(16000, dtype="float32")
        speech_to_text = MagicMock()
        speech_to_text.transcribe.side_effect = SpeechRecognitionError("mic failed")
        text_to_speech = MagicMock()

        manager = VoiceManager(
            conversation=conversation,
            recorder=recorder,
            speech_to_text=speech_to_text,
            text_to_speech=text_to_speech,
        )

        result = manager.listen_and_respond()

        self.assertEqual(result.heard, "")
        self.assertIn("failed", result.response.lower())
        conversation.generate_response.assert_not_called()

    def test_text_to_speech_failure_still_returns_response(self) -> None:
        conversation = MagicMock()
        conversation.generate_response.return_value = "It is 10:42 PM."
        recorder = MagicMock()
        recorder.record.return_value = np.ones(16000, dtype="float32")
        speech_to_text = MagicMock()
        speech_to_text.transcribe.return_value = "What time is it?"
        text_to_speech = MagicMock()
        text_to_speech.speak.side_effect = TextToSpeechError("speaker failed")

        manager = VoiceManager(
            conversation=conversation,
            recorder=recorder,
            speech_to_text=speech_to_text,
            text_to_speech=text_to_speech,
        )

        result = manager.listen_and_respond()

        self.assertIn("10:42", result.response)
        self.assertIn("speech playback failed", result.response.lower())


class TestSpeechToText(unittest.TestCase):
    """Unit tests for speech-to-text behavior."""

    def test_empty_audio_returns_empty_string(self) -> None:
        stt = SpeechToText()

        result = stt.transcribe(np.array([], dtype="float32"))

        self.assertEqual(result, "")


class TestAudioRecorder(unittest.TestCase):
    """Unit tests for audio recorder configuration."""

    def test_defaults(self) -> None:
        recorder = AudioRecorder()
        self.assertEqual(recorder.sample_rate, 16000)


if __name__ == "__main__":
    unittest.main()
