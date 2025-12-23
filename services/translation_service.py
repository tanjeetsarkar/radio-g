import logging
from typing import Dict, Optional
from abc import ABC, abstractmethod
import time
import hashlib

logger = logging.getLogger(__name__)


class TranslationProvider(ABC):
    """Abstract base class for translation providers"""
    
    @abstractmethod
    def translate(self, text: str, target_language: str, source_language: str = "auto") -> str:
        """Translate text to target language"""
        pass
    
    @abstractmethod
    def summarize(self, text: str, max_length: int = 150) -> str:
        """Summarize text to specified length"""
        pass
    
    @abstractmethod
    def translate_and_summarize(
        self, 
        text: str, 
        target_language: str,
        max_length: int = 150
    ) -> Dict[str, str]:
        """Translate and summarize in one call (more efficient)"""
        pass


class MockTranslationProvider(TranslationProvider):
    """
    Mock translation provider for development
    Returns placeholder text without actual API calls
    """
    
    def __init__(self):
        self.call_count = 0
        logger.info("✓ Mock Translation Provider initialized (no API key needed)")
    
    def translate(self, text: str, target_language: str, source_language: str = "auto") -> str:
        """Mock translation - returns modified text with language marker"""
        self.call_count += 1
        
        # Simulate API delay
        time.sleep(0.1)
        
        # Add language marker to show it was "translated"
        language_markers = {
            'en': '[EN]',
            'hi': '[HI-हिंदी]',
            'bn': '[BN-বাংলা]'
        }
        
        marker = language_markers.get(target_language, f'[{target_language.upper()}]')
        
        # Keep first 200 chars and add marker
        translated = f"{marker} {text[:200]}..."
        
        logger.debug(f"Mock translated to {target_language}: {text[:50]}...")
        return translated
    
    def summarize(self, text: str, max_length: int = 150) -> str:
        """Mock summarization - returns truncated text"""
        self.call_count += 1
        
        # Simulate API delay
        time.sleep(0.1)
        
        # Simple truncation with ellipsis
        if len(text) <= max_length:
            summary = text
        else:
            # Try to break at sentence
            summary = text[:max_length].rsplit('.', 1)[0] + '...'
        
        logger.debug(f"Mock summarized: {len(text)} -> {len(summary)} chars")
        return summary
    
    def translate_and_summarize(
        self, 
        text: str, 
        target_language: str,
        max_length: int = 150
    ) -> Dict[str, str]:
        """Mock translation + summarization"""
        self.call_count += 1
        
        # Simulate API delay
        time.sleep(0.15)
        
        # First summarize, then translate
        summary = self.summarize(text, max_length)
        translated_summary = self.translate(summary, target_language)
        
        return {
            'original': text,
            'summary': summary,
            'translated_summary': translated_summary,
            'target_language': target_language,
            'source_language': 'en',  # Mock detected language
            'provider': 'mock'
        }


class GeminiTranslationProvider(TranslationProvider):
    """
    Real Gemini API provider (placeholder for later)
    TODO: Implement when API key is available
    """
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        """
        Initialize Gemini API client
        
        Args:
            api_key: Gemini API key
            model: Model to use (gemini-1.5-flash or gemini-1.5-pro)
        """
        self.api_key = api_key
        self.model = model
        self.call_count = 0
        
        # TODO: Initialize actual Gemini client
        # import google.generativeai as genai
        # genai.configure(api_key=api_key)
        # self.client = genai.GenerativeModel(model)
        
        logger.info(f"✓ Gemini Translation Provider initialized (model: {model})")
    
    def translate(self, text: str, target_language: str, source_language: str = "auto") -> str:
        """
        Translate using Gemini API
        
        TODO: Implement actual API call
        """
        self.call_count += 1
        
        # TODO: Replace with actual Gemini API call
        # prompt = f"Translate the following text to {target_language}:\n\n{text}"
        # response = self.client.generate_content(prompt)
        # return response.text
        
        # For now, fallback to mock
        logger.warning("Gemini API not implemented yet, using mock")
        mock = MockTranslationProvider()
        return mock.translate(text, target_language, source_language)
    
    def summarize(self, text: str, max_length: int = 150) -> str:
        """
        Summarize using Gemini API
        
        TODO: Implement actual API call
        """
        self.call_count += 1
        
        # TODO: Replace with actual Gemini API call
        # prompt = f"""Summarize the following news article in approximately {max_length} characters.
        # Make it suitable for a radio broadcast (30-60 seconds when spoken).
        # Keep the most important information.
        
        # Article: {text}
        # """
        # response = self.client.generate_content(prompt)
        # return response.text
        
        # For now, fallback to mock
        logger.warning("Gemini API not implemented yet, using mock")
        mock = MockTranslationProvider()
        return mock.summarize(text, max_length)
    
    def translate_and_summarize(
        self, 
        text: str, 
        target_language: str,
        max_length: int = 150
    ) -> Dict[str, str]:
        """
        Translate and summarize in one Gemini API call (more efficient)
        
        TODO: Implement actual API call
        """
        self.call_count += 1
        
        # TODO: Replace with actual Gemini API call
        # prompt = f"""Process this news article for a multilingual radio broadcast:
        
        # 1. Summarize to approximately {max_length} characters (30-60 seconds when read)
        # 2. Translate the summary to {target_language}
        # 3. Make it engaging and suitable for audio broadcast
        
        # Article: {text}
        
        # Respond in JSON format:
        # {{
        #   "summary": "English summary",
        #   "translated_summary": "Translated summary",
        #   "target_language": "{target_language}"
        # }}
        # """
        # response = self.client.generate_content(prompt)
        # result = json.loads(response.text)
        
        # For now, fallback to mock
        logger.warning("Gemini API not implemented yet, using mock")
        mock = MockTranslationProvider()
        return mock.translate_and_summarize(text, target_language, max_length)


class TranslationService:
    """
    Main translation service that manages providers
    Easy to switch between mock and real providers
    """
    
    def __init__(
        self, 
        provider: str = "mock",
        api_key: Optional[str] = None,
        model: str = "gemini-1.5-flash"
    ):
        """
        Initialize translation service
        
        Args:
            provider: 'mock' or 'gemini'
            api_key: API key for real provider
            model: Model to use for Gemini
        """
        self.provider_name = provider
        
        if provider == "mock":
            self.provider = MockTranslationProvider()
        elif provider == "gemini":
            if not api_key:
                logger.warning("No API key provided, falling back to mock provider")
                self.provider = MockTranslationProvider()
            else:
                self.provider = GeminiTranslationProvider(api_key, model)
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        # Cache for translations (optional optimization)
        self.cache = {}
        
        logger.info(f"✓ Translation Service initialized with provider: {provider}")
    
    def _get_cache_key(self, text: str, target_language: str, operation: str) -> str:
        """Generate cache key for translation"""
        data = f"{operation}:{target_language}:{text[:100]}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def translate(
        self, 
        text: str, 
        target_language: str, 
        source_language: str = "auto",
        use_cache: bool = True
    ) -> str:
        """Translate text with optional caching"""
        
        if use_cache:
            cache_key = self._get_cache_key(text, target_language, "translate")
            if cache_key in self.cache:
                logger.debug("Using cached translation")
                return self.cache[cache_key]
        
        result = self.provider.translate(text, target_language, source_language)
        
        if use_cache:
            self.cache[cache_key] = result
        
        return result
    
    def summarize(self, text: str, max_length: int = 150, use_cache: bool = True) -> str:
        """Summarize text with optional caching"""
        
        if use_cache:
            cache_key = self._get_cache_key(text, "summary", f"summarize_{max_length}")
            if cache_key in self.cache:
                logger.debug("Using cached summary")
                return self.cache[cache_key]
        
        result = self.provider.summarize(text, max_length)
        
        if use_cache:
            self.cache[cache_key] = result
        
        return result
    
    def translate_and_summarize(
        self, 
        text: str, 
        target_language: str,
        max_length: int = 150,
        use_cache: bool = True
    ) -> Dict[str, str]:
        """Translate and summarize in one call"""
        
        if use_cache:
            cache_key = self._get_cache_key(
                text, target_language, f"translate_summarize_{max_length}"
            )
            if cache_key in self.cache:
                logger.debug("Using cached translation+summary")
                return self.cache[cache_key]
        
        result = self.provider.translate_and_summarize(text, target_language, max_length)
        
        if use_cache:
            self.cache[cache_key] = result
        
        return result
    
    def get_stats(self) -> Dict:
        """Get service statistics"""
        return {
            'provider': self.provider_name,
            'total_calls': self.provider.call_count,
            'cache_size': len(self.cache)
        }


# Example usage
if __name__ == "__main__":
    # Mock provider (for development)
    service = TranslationService(provider="mock")
    
    sample_text = """
    Breaking news: Tech giant announces revolutionary AI breakthrough.
    The company unveiled a new artificial intelligence system that can 
    understand and generate human-like responses in multiple languages.
    This development marks a significant milestone in the field of AI research.
    """
    
    print("=== MOCK TRANSLATION SERVICE ===\n")
    
    # Test translation
    print("1. Translation to Hindi:")
    hindi = service.translate(sample_text, "hi")
    print(f"{hindi}\n")
    
    # Test summarization
    print("2. Summarization:")
    summary = service.summarize(sample_text, max_length=100)
    print(f"{summary}\n")
    
    # Test combined
    print("3. Translate + Summarize (Bengali):")
    result = service.translate_and_summarize(sample_text, "bn", max_length=120)
    print(f"Summary: {result['summary']}")
    print(f"Translated: {result['translated_summary']}\n")
    
    # Stats
    print("4. Service Stats:")
    print(service.get_stats())