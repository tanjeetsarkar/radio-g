import logging
from typing import Dict, Optional
from abc import ABC, abstractmethod
import time
import hashlib
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
    """Abstract base class for translation providers"""
    
    @abstractmethod
    def translate(self, text: str, target_language: str) -> str:
        pass
    
    @abstractmethod
    def summarize(self, text: str, max_length: int = 150) -> str:
        pass
    
    @abstractmethod
    def translate_and_summarize(self, text: str, target_language: str, max_length: int = 150) -> Dict[str, str]:
        pass


class MockTranslationProvider(TranslationProvider):
    """Mock provider for testing without API costs"""
    
    def __init__(self):
        self.call_count = 0
        logger.info("✓ Mock Translation Provider initialized")
    
    def translate(self, text: str, target_language: str) -> str:
        self.call_count += 1
        time.sleep(0.1)
        return f"[{target_language.upper()}] {text[:50]}..."
    
    def summarize(self, text: str, max_length: int = 150) -> str:
        self.call_count += 1
        time.sleep(0.1)
        return text[:max_length] + "..."
    
    def translate_and_summarize(self, text: str, target_language: str, max_length: int = 150) -> Dict[str, str]:
        self.call_count += 1
        time.sleep(0.15)
        summary = self.summarize(text, max_length)
        return {
            'original': text[:50],
            'summary': summary,
            'translated_summary': f"[{target_language.upper()}] {summary}",
            'target_language': target_language,
            'provider': 'mock'
        }


class GeminiTranslationProvider(TranslationProvider):
    """
    Real Gemini Provider using the latest Google Gen AI SDK (v1.0+)
    Ref: https://github.com/googleapis/python-genai
    """
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        if not GEMINI_AVAILABLE:
            raise ImportError("google-genai package not installed. Run 'uv add google-genai'")

        self.api_key = api_key
        self.model_name = model
        self.call_count = 0
        
        # Initialize the V1 Client
        self.client = genai.Client(api_key=api_key)
        
        logger.info(f"✓ Gemini Translation Provider initialized (model: {model})")
    
    def translate(self, text: str, target_language: str) -> str:
        self.call_count += 1
        
        prompt = f"Translate the following text into {target_language}. Return ONLY the translation."
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, text],
                config=types.GenerateContentConfig(
                    temperature=0.3
                )
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini Translation Error: {e}")
            raise

    def summarize(self, text: str, max_length: int = 150) -> str:
        self.call_count += 1
        
        prompt = f"Summarize this into a radio script approx {max_length} characters long."
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, text],
                config=types.GenerateContentConfig(
                    temperature=0.3
                )
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini Summarization Error: {e}")
            raise
    
    def translate_and_summarize(
        self, 
        text: str, 
        target_language: str,
        max_length: int = 150
    ) -> Dict[str, str]:
        """
        Uses Gemini's Structured Output (Schema) feature for 100% reliable JSON.
        """
        self.call_count += 1
        
        prompt = f"""
        You are a news editor. 
        1. Summarize the article for a radio broadcast (approx {max_length} chars).
        2. Translate that summary into {target_language}.
        """
        
        try:
            # New V1 SDK Pattern: Pass the Pydantic model directly to response_schema
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, text],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=TranslationOutput, # Strict Schema Enforcement
                    temperature=0.2
                )
            )
            
            # The SDK automatically handles JSON parsing if we used a schema
            # We can parse the JSON string into our Pydantic model
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
            logger.error(f"Gemini Translate & Summarize Error: {e}")
            raise


class TranslationService:
    """Service Factory"""
    
    def __init__(
        self, 
        provider: str = "mock",
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash" 
    ):
        self.provider_name = provider
        self.cache = {}
        
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
        
        logger.info(f"✓ Translation Service initialized: {provider}")
    
    def translate_and_summarize(self, text: str, target_language: str, max_length: int = 200) -> Dict[str, str]:
        # Simple caching
        key = hashlib.md5(f"{text[:50]}:{target_language}".encode()).hexdigest()
        if key in self.cache:
            return self.cache[key]
            
        result = self.provider.translate_and_summarize(text, target_language, max_length)
        self.cache[key] = result
        return result
    
    def get_stats(self):
        return {'provider': self.provider_name, 'total_calls': self.provider.call_count}