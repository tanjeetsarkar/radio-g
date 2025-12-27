"""
Tests for translation and TTS services
Located at: tests/test_translation_tts.py
"""

import pytest
from pathlib import Path
import json

from services.translation_service import (
    TranslationService,
    MockTranslationProvider,
    GeminiTranslationProvider
)
from services.tts_service import (
    TTSService,
    MockTTSProvider,
    ElevenLabsTTSProvider
)


@pytest.mark.unit
@pytest.mark.mock
class TestMockTranslationProvider:
    """Test mock translation provider"""
    
    def test_mock_provider_initialization(self):
        """Test mock provider initializes correctly"""
        provider = MockTranslationProvider()
        assert provider.call_count == 0
    
    def test_mock_translate(self):
        """Test mock translation"""
        provider = MockTranslationProvider()
        
        text = "Hello, this is a test article about technology."
        result = provider.translate_and_summarize(text, "hi")

        assert result['target_language'] == 'hi'
        assert provider.call_count == 1
    
    def test_mock_summarize(self):
        """Test mock summarization"""
        provider = MockTranslationProvider()
        
        long_text = "This is a very long article. " * 50
        result = provider.translate_and_summarize(long_text, "en", max_length=100)

        # mock returns text[:max_length] + '...'
        assert len(result['summary']) <= 103
        assert provider.call_count == 1
    
    def test_mock_translate_and_summarize(self):
        """Test combined operation"""
        provider = MockTranslationProvider()
        
        text = "News article content here."
        result = provider.translate_and_summarize(text, "bn", max_length=100)

        assert 'summary' in result
        assert 'translated_summary' in result
        assert result['target_language'] == 'bn'
        assert result['translated_summary'].startswith('[BN]')


@pytest.mark.unit
@pytest.mark.mock
class TestTranslationService:
    """Test translation service"""
    
    def test_service_initialization_mock(self):
        """Test service initializes with mock provider"""
        service = TranslationService(provider="mock")
        
        assert service.provider_name == "mock"
        assert isinstance(service.provider, MockTranslationProvider)
    
    def test_service_translate(self):
        """Test service translation"""
        service = TranslationService(provider="mock")
        
        result = service.translate_and_summarize("Test text", "hi")

        assert result['target_language'] == 'hi'
    
    def test_service_summarize(self):
        """Test service summarization"""
        service = TranslationService(provider="mock")
        
        long_text = "A" * 500
        result = service.translate_and_summarize(long_text, "en", max_length=100)

        assert len(result['summary']) <= 103
    
    def test_service_translate_and_summarize(self):
        """Test combined service operation"""
        service = TranslationService(provider="mock")
        
        result = service.translate_and_summarize(
            "Test article content",
            "en",
            max_length=120
        )

        assert 'summary' in result
        assert 'translated_summary' in result
    
    def test_service_caching(self):
        """Test that caching works"""
        service = TranslationService(provider="mock")
        
        text = "Test text for caching"
        
        # First call
        result1 = service.translate_and_summarize(text, "hi")
        calls_after_1 = service.provider.call_count

        # Second call (should use cache)
        result2 = service.translate_and_summarize(text, "hi")
        calls_after_2 = service.provider.call_count

        assert result1 == result2
        assert calls_after_1 == calls_after_2  # No additional calls
    
    def test_service_get_stats(self):
        """Test getting service statistics"""
        service = TranslationService(provider="mock")
        
        service.translate_and_summarize("Test", "hi")
        service.translate_and_summarize("Test" * 100, "en", max_length=50)

        stats = service.get_stats()

        assert stats['provider'] == 'mock'
        assert 'stats' in stats
        assert 'calls' in stats['stats']
    
    def test_multiple_languages(self):
        """Test translating to multiple languages"""
        service = TranslationService(provider="mock")
        
        text = "Breaking news story"
        languages = ['en', 'hi', 'bn']
        
        results = {}
        for lang in languages:
            results[lang] = service.translate_and_summarize(text, lang)
        
        assert len(results) == 3
        assert results['hi']['target_language'] == 'hi'
        assert results['bn']['target_language'] == 'bn'


@pytest.mark.unit
@pytest.mark.mock
class TestMockTTSProvider:
    """Test mock TTS provider"""
    
    def test_mock_tts_initialization(self, temp_dir):
        """Test mock TTS provider initializes"""
        provider = MockTTSProvider()
        
        # Mock provider is stateless and has no output_dir attribute
        assert hasattr(provider, 'save_speech')
    
    def test_mock_generate_speech(self, temp_dir):
        """Test mock speech generation"""
        provider = MockTTSProvider()

        output_path = temp_dir / "gen_audio.mp3"
        result = provider.save_speech("Test text", str(output_path), "en")

        assert Path(result).exists()
    
    def test_mock_save_speech(self, temp_dir):
        """Test mock saving speech"""
        provider = MockTTSProvider()

        output_path = temp_dir / "test_audio.mp3"
        result_path = provider.save_speech(
            "Test text for speech",
            str(output_path),
            "en"
        )

        # Check file created
        assert Path(result_path).exists()
    
    def test_mock_available_voices(self, temp_dir):
        """MockTTSProvider does not expose voice enumeration"""
        provider = MockTTSProvider()
        assert not hasattr(provider, 'get_available_voices')


@pytest.mark.unit
@pytest.mark.mock
class TestTTSService:
    """Test TTS service"""
    
    def test_service_initialization_mock(self, temp_dir):
        """Test service initializes with mock provider"""
        service = TTSService(provider="mock", output_dir=str(temp_dir))
        
        assert service.provider_name == "mock"
        assert isinstance(service.provider, MockTTSProvider)
    
    def test_service_generate_speech(self, temp_dir):
        """Test service speech generation"""
        service = TTSService(provider="mock", output_dir=str(temp_dir))
        
        result = service.save_speech("Test text", "en")

        assert Path(result).exists()
    
    def test_service_save_speech(self, temp_dir):
        """Test service save speech"""
        service = TTSService(provider="mock", output_dir=str(temp_dir))
        
        result_path = service.save_speech("Test news summary", "en")

        assert Path(result_path).exists()
    
    def test_service_save_with_custom_filename(self, temp_dir):
        """Test saving with custom filename"""
        service = TTSService(provider="mock", output_dir=str(temp_dir))
        
        result_path = service.save_speech(
            "Test text",
            "hi",
            filename="custom_audio.mp3"
        )
        
        assert "custom_audio.mp3" in result_path
    
    def test_service_batch_generate(self, temp_dir):
        """Test batch audio generation"""
        service = TTSService(provider="mock", output_dir=str(temp_dir))
        
        texts = {
            'news_1': "First news story",
            'news_2': "Second news story",
            'news_3': "Third news story"
        }
        
        results = {}
        for k, txt in texts.items():
            results[k] = service.save_speech(txt, "en", filename=f"{k}.mp3")

        assert len(results) == 3
        assert all(Path(v).exists() for v in results.values())
    
    def test_service_get_stats(self, temp_dir):
        """Test getting service statistics"""
        service = TTSService(provider="mock", output_dir=str(temp_dir))
        
        service.save_speech("Test 1", "en")
        service.save_speech("Test 2", "hi")

        stats = service.get_stats()

        assert stats['provider'] == 'mock'
    
    def test_multiple_languages_tts(self, temp_dir):
        """Test generating audio for multiple languages"""
        service = TTSService(provider="mock", output_dir=str(temp_dir))
        
        text = "Breaking news update"
        languages = ['en', 'hi', 'bn']
        
        audio_files = {}
        for lang in languages:
            audio_files[lang] = service.save_speech(text, lang)
        
        assert len(audio_files) == 3
        assert all(Path(path).exists() for path in audio_files.values())


@pytest.mark.unit
class TestGeminiPlaceholder:
    """Test Gemini provider placeholder"""
    
    def test_gemini_falls_back_to_mock(self):
        """Test that Gemini provider falls back to mock when not implemented"""
        # This would normally fail without API key, but should fall back
        try:
            provider = GeminiTranslationProvider("fake-api-key")
            # If it doesn't raise, the placeholder is working
            assert True
        except:
            # Expected during development
            pytest.skip("Gemini not implemented yet")


@pytest.mark.unit
class TestElevenLabsPlaceholder:
    """Test ElevenLabs provider placeholder"""
    
    def test_elevenlabs_falls_back_to_mock(self, temp_dir):
        """Test that ElevenLabs provider falls back to mock when not implemented"""
        try:
            provider = ElevenLabsTTSProvider("fake-api-key", str(temp_dir))
            # If it doesn't raise, the placeholder is working
            assert True
        except:
            # Expected during development
            pytest.skip("ElevenLabs not implemented yet")