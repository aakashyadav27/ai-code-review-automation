"""
Multi-provider LLM client with automatic fallback.
Supports Gemini (primary) and Groq (fallback).
"""
import os
import time
from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Standard response format from any LLM provider."""
    text: str
    provider: str
    model: str
    tokens_used: int = 0


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def generate(self, prompt: str) -> LLMResponse:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass


class GeminiProvider(LLMProvider):
    """Google Gemini provider with key rotation."""
    
    def __init__(self, api_keys: List[str], model: str = "gemini-2.0-flash"):
        self.api_keys = api_keys
        self.model_name = model
        self.current_key_index = 0
        self.rate_limited_until = {}  # key -> timestamp
        self._genai = None
        self._model = None
    
    @property
    def name(self) -> str:
        return "gemini"
    
    def _get_next_available_key(self) -> Optional[str]:
        """Get next available key that isn't rate limited."""
        now = time.time()
        
        for _ in range(len(self.api_keys)):
            key = self.api_keys[self.current_key_index]
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            
            # Check if key is rate limited
            if key in self.rate_limited_until:
                if now < self.rate_limited_until[key]:
                    continue
                else:
                    del self.rate_limited_until[key]
            
            return key
        
        return None  # All keys rate limited
    
    def is_available(self) -> bool:
        return len(self.api_keys) > 0 and self._get_next_available_key() is not None
    
    def generate(self, prompt: str) -> LLMResponse:
        import google.generativeai as genai
        
        key = self._get_next_available_key()
        if not key:
            raise Exception("All Gemini API keys are rate limited")
        
        genai.configure(api_key=key)
        model = genai.GenerativeModel(self.model_name)
        
        try:
            response = model.generate_content(prompt)
            return LLMResponse(
                text=response.text,
                provider="gemini",
                model=self.model_name
            )
        except Exception as e:
            error_msg = str(e)
            if "ResourceExhausted" in error_msg or "429" in error_msg:
                # Mark this key as rate limited for 60 seconds
                self.rate_limited_until[key] = time.time() + 60
            raise


class GroqProvider(LLMProvider):
    """Groq provider for fast inference."""
    
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model_name = model
        self._client = None
    
    @property
    def name(self) -> str:
        return "groq"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def _get_client(self):
        if self._client is None:
            from groq import Groq
            self._client = Groq(api_key=self.api_key)
        return self._client
    
    def generate(self, prompt: str) -> LLMResponse:
        client = self._get_client()
        
        response = client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2048
        )
        
        return LLMResponse(
            text=response.choices[0].message.content,
            provider="groq",
            model=self.model_name,
            tokens_used=response.usage.total_tokens if response.usage else 0
        )


class MultiProviderLLM:
    """
    Multi-provider LLM client with automatic fallback.
    Tries Gemini first, falls back to Groq if rate limited.
    """
    
    def __init__(self):
        self.providers: List[LLMProvider] = []
        self._load_providers()
    
    def _load_providers(self):
        """Load providers from environment variables."""
        
        # Load Gemini keys
        gemini_keys = []
        multi_keys = os.environ.get("GEMINI_API_KEYS", "")
        if multi_keys:
            gemini_keys.extend([k.strip() for k in multi_keys.split(",") if k.strip()])
        single_key = os.environ.get("GEMINI_API_KEY", "")
        if single_key and single_key not in gemini_keys:
            gemini_keys.append(single_key)
        
        if gemini_keys:
            self.providers.append(GeminiProvider(gemini_keys))
        
        # Load Groq key
        groq_key = os.environ.get("GROQ_API_KEY", "")
        if groq_key:
            self.providers.append(GroqProvider(groq_key))
    
    def generate(self, prompt: str) -> LLMResponse:
        """
        Generate content using available providers.
        Falls back to next provider on failure.
        """
        errors = []
        
        for provider in self.providers:
            if not provider.is_available():
                continue
            
            try:
                return provider.generate(prompt)
            except Exception as e:
                errors.append(f"{provider.name}: {str(e)[:100]}")
                continue
        
        # All providers failed
        raise Exception(f"All LLM providers failed: {'; '.join(errors)}")
    
    def get_status(self) -> dict:
        """Get status of all providers."""
        return {
            "providers": [
                {
                    "name": p.name,
                    "available": p.is_available()
                }
                for p in self.providers
            ]
        }


# Global instance
_llm_client: Optional[MultiProviderLLM] = None


def get_llm_client() -> MultiProviderLLM:
    """Get or create the global LLM client."""
    global _llm_client
    if _llm_client is None:
        _llm_client = MultiProviderLLM()
    return _llm_client


def reset_llm_client():
    """Reset the global LLM client."""
    global _llm_client
    _llm_client = None
