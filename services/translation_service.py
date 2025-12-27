import logging
from typing import Dict, Optional
from abc import ABC, abstractmethod
import time
import hashlib
import json
from pydantic import BaseModel, Field

# Check for new SDK
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

logger = logging.getLogger(__name__)

# --- Data Models for Structured Output ---
class TranslationOutput(BaseModel):
    summary: str = Field(description="A concise summary of the article in English")
    translated_summary: str = Field(description="The summary translated into the target language")
    target_language: str = Field(description="The language code of the translation")

class TranslationProvider(ABC):
    @abstractmethod
    def translate_and_summarize(self, text: str, target_language: str, max_length: int = 150) -> Dict[str, str]:
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict:
        pass

class MockTranslationProvider(TranslationProvider):
    def __init__(self):
        self.call_count = 0
        logger.info("✓ Mock Translation Provider initialized")
    
    def translate_and_summarize(self, text: str, target_language: str, max_length: int = 150) -> Dict[str, str]:
        self.call_count += 1
        time.sleep(0.1)
        summary = text[:max_length] + "..."
        return {
            'original': text[:50],
            'summary': summary,
            'translated_summary': f"[{target_language.upper()}] {summary}",
            'target_language': target_language,
            'provider': 'mock'
        }
    
    def get_stats(self) -> Dict:
        return {'calls': self.call_count}

class GeminiTranslationProvider(TranslationProvider):
    """Real Gemini Provider using Google Gen AI SDK"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        if not GEMINI_AVAILABLE:
            raise ImportError("google-genai package not installed. Run 'uv add google-genai'")

        self.api_key = api_key
        self.model_name = model
        self.call_count = 0
        self.client = genai.Client(api_key=api_key)
        logger.info(f"✓ Gemini Translation Provider initialized (model: {model})")
    
    def translate_and_summarize(self, text: str, target_language: str, max_length: int = 150) -> Dict[str, str]:
        self.call_count += 1
        
        prompt = f"""
        You are a news editor. 
        1. Summarize the article for a radio broadcast (approx {max_length} chars).
        2. Translate that summary into {target_language}.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, text],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=TranslationOutput,
                    temperature=0.1
                )
            )
            
            if not response.text:
                raise ValueError("Empty response from Gemini")
                
            data = TranslationOutput.model_validate_json(response.text)
            
            return {
                'original': text[:100] + "...",
                'summary': data.summary,
                'translated_summary': data.translated_summary,
                'target_language': data.target_language,
                'provider': 'gemini'
            }
        except Exception as e:
            logger.error(f"Gemini Error: {e}")
            raise

    def get_stats(self) -> Dict:
        return {'calls': self.call_count}

class TranslationService:
    def __init__(self, provider: str = "mock", api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        self.provider_name = provider
        self.cache = {}
        
        if provider == "gemini":
            if not api_key:
                logger.warning("No API key provided, falling back to mock.")
                self.provider = MockTranslationProvider()
            else:
                self.provider = GeminiTranslationProvider(api_key, model)
        else:
            self.provider = MockTranslationProvider()
        
    def translate_and_summarize(self, text: str, target_language: str, max_length: int = 200) -> Dict[str, str]:
        # Simple caching
        key = hashlib.md5(f"{text[:50]}:{target_language}".encode()).hexdigest()
        if key in self.cache:
            return self.cache[key]
            
        result = self.provider.translate_and_summarize(text, target_language, max_length)
        self.cache[key] = result
        return result
    
    def get_stats(self):
        return {'provider': self.provider_name, 'stats': self.provider.get_stats()}