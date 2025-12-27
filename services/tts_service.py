import logging
from typing import Optional, Dict
from abc import ABC, abstractmethod
import time
from pathlib import Path
import hashlib

# Check for ElevenLabs
try:
    from elevenlabs.client import ElevenLabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

logger = logging.getLogger(__name__)

class TTSProvider(ABC):
    @abstractmethod
    def save_speech(self, text: str, output_path: str, language: str) -> str:
        pass

class MockTTSProvider(TTSProvider):
    def save_speech(self, text: str, output_path: str, language: str) -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        # Create empty file
        with open(output_path, 'wb') as f:
            f.write(b'')
        return output_path

class ElevenLabsTTSProvider(TTSProvider):
    def __init__(self, api_key: str, model: str = "eleven_multilingual_v2"):
        if not ELEVENLABS_AVAILABLE:
            raise ImportError("elevenlabs package not installed. Run 'uv add elevenlabs'")
            
        self.client = ElevenLabs(api_key=api_key)
        self.model = model
        # Voice IDs
        self.voices = {
            'en': 'JBFqnCBsd6RMkjVDRZzb', # George
            'hi': 'D38z5RcWu1voky8WS1ja', # Fin
            'bn': 'D38z5RcWu1voky8WS1ja'  # Fin
        }
        logger.info("✓ ElevenLabs Provider initialized")

    def save_speech(self, text: str, output_path: str, language: str) -> str:
        voice_id = self.voices.get(language, self.voices['en'])
        
        try:
            logger.info(f"Generating ElevenLabs audio ({language})...")
            audio_generator = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id=self.model
            )
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save the generator output to file
            with open(output_path, 'wb') as f:
                for chunk in audio_generator:
                    f.write(chunk)
            
            return output_path
        except Exception as e:
            logger.error(f"ElevenLabs Error: {e}")
            raise

class TTSService:
    def __init__(self, provider: str = "mock", api_key: Optional[str] = None, output_dir: str = "audio_output"):
        self.provider_name = provider
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        if provider == "elevenlabs":
            if not api_key:
                logger.warning("No API key provided, falling back to mock.")
                self.provider = MockTTSProvider()
            else:
                self.provider = ElevenLabsTTSProvider(api_key)
        else:
            self.provider = MockTTSProvider()

    def save_speech(self, text: str, language: str, filename: Optional[str] = None) -> str:
        if not filename:
            filename = f"audio_{language}_{int(time.time())}.mp3"
        output_path = self.output_dir / filename
        return self.provider.save_speech(text, str(output_path), language)
        
    def get_stats(self):
        return {'provider': self.provider_name}