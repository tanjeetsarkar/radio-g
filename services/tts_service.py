import logging
from typing import Optional
from abc import ABC, abstractmethod
import time
from pathlib import Path
import json

# Import ElevenLabs client (wrapped in try/except to avoid crashing if not installed)
try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import VoiceSettings

    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

logger = logging.getLogger(__name__)


class TTSProvider(ABC):
    """Abstract base class for Text-to-Speech providers"""

    @abstractmethod
    def generate_speech(
        self, text: str, language: str, voice_id: Optional[str] = None
    ) -> bytes:
        """Generate speech audio from text"""
        pass

    @abstractmethod
    def save_speech(
        self, text: str, output_path: str, language: str, voice_id: Optional[str] = None
    ) -> str:
        """Generate and save speech to file"""
        pass


class MockTTSProvider(TTSProvider):
    """
    Mock TTS provider for development
    Creates placeholder audio metadata without actual audio generation
    """

    def __init__(self, output_dir: str = "audio_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.call_count = 0

        self.voices = {
            "en": {"voice_id": "mock-en", "name": "English Mock"},
            "hi": {"voice_id": "mock-hi", "name": "Hindi Mock"},
            "bn": {"voice_id": "mock-bn", "name": "Bengali Mock"},
        }
        logger.info(f"✓ Mock TTS Provider initialized (output: {output_dir})")

    def generate_speech(
        self, text: str, language: str, voice_id: Optional[str] = None
    ) -> bytes:
        self.call_count += 1
        time.sleep(0.5)  # Simulate latency
        return b"mock_audio_bytes"

    def save_speech(
        self, text: str, output_path: str, language: str, voice_id: Optional[str] = None
    ) -> str:
        self.call_count += 1

        # Create metadata file instead of real audio
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        metadata = {
            "text": text,
            "language": language,
            "provider": "mock",
            "estimated_duration": len(text.split()) / 2.5,  # Rough guess
        }

        # Save metadata
        meta_path = path.with_suffix(".json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        # Create empty dummy file so downstream tools don't crash
        with open(output_path, "wb") as f:
            f.write(b"")

        logger.info(f"Mock saved: {output_path}")
        return str(output_path)


class ElevenLabsTTSProvider(TTSProvider):
    """
    Real ElevenLabs TTS provider
    """

    def __init__(
        self,
        api_key: str,
        output_dir: str = "audio_output",
        model: str = "eleven_multilingual_v2",
    ):
        if not ELEVENLABS_AVAILABLE:
            raise ImportError(
                "elevenlabs package not installed. Run 'pip install elevenlabs'"
            )

        self.client = ElevenLabs(api_key=api_key)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.model = model
        self.call_count = 0

        # Voice IDs (You can customize these from the ElevenLabs Voice Lab)
        self.voice_mapping = {
            # Default "Rachel" voice (Good for English)
            "en": "21m00Tcm4TlvDq8ikWAM",
            # "Fin" (Good for formal news) - Replace with specific Hindi/Bengali trained voices if available
            "hi": "D38z5RcWu1voky8WS1ja",
            "bn": "D38z5RcWu1voky8WS1ja",
        }

        logger.info(f"✓ ElevenLabs TTS Provider initialized (model: {model})")

    def generate_speech(
        self, text: str, language: str, voice_id: Optional[str] = None
    ) -> bytes:
        """Generate speech using ElevenLabs API"""
        self.call_count += 1

        # Determine voice ID
        if not voice_id:
            voice_id = self.voice_mapping.get(language, self.voice_mapping["en"])

        try:
            logger.info(f"Generating ElevenLabs audio ({language})...")

            # The convert method returns a generator of bytes
            audio_generator = self.client.text_to_speech.convert(
                text=text, voice_id=voice_id, model_id=self.model
            )

            # Consume the generator to get full bytes
            audio_data = b"".join(audio_generator)
            return audio_data

        except Exception as e:
            logger.error(f"ElevenLabs API Error: {e}")
            raise e

    def save_speech(
        self, text: str, output_path: str, language: str, voice_id: Optional[str] = None
    ) -> str:
        """Generate and save speech to file"""
        # Generate the audio bytes
        audio_data = self.generate_speech(text, language, voice_id)

        # Save to disk
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "wb") as f:
            f.write(audio_data)

        logger.info(f"✓ Saved real audio: {output_path} ({len(audio_data)} bytes)")
        return str(output_path)


class TTSService:
    """
    Main Text-to-Speech service wrapper
    """

    def __init__(
        self,
        provider: str = "mock",
        api_key: Optional[str] = None,
        output_dir: str = "audio_output",
        model: str = "eleven_multilingual_v2",
    ):
        self.provider_name = provider
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        if provider == "mock":
            self.provider = MockTTSProvider(output_dir)
        elif provider == "elevenlabs":
            if not api_key:
                logger.warning("No API key provided! Falling back to Mock provider.")
                self.provider = MockTTSProvider(output_dir)
            else:
                self.provider = ElevenLabsTTSProvider(api_key, output_dir, model)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def save_speech(
        self, text: str, language: str, filename: Optional[str] = None
    ) -> str:
        if not filename:
            # Create a simple safe filename
            safe_text = "".join([c for c in text[:20] if c.isalnum()])
            timestamp = int(time.time())
            filename = f"audio_{language}_{timestamp}_{safe_text}.mp3"

        output_path = self.output_dir / filename
        return self.provider.save_speech(text, str(output_path), language)

    def get_stats(self):
        return {"provider": self.provider_name, "total_calls": self.provider.call_count}
