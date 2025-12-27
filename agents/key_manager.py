"""
API Key Manager with rotation support.
Handles multiple API keys and rotates between them to avoid rate limits.
"""
import os
import time
import random
from typing import List, Optional
from dataclasses import dataclass
import google.generativeai as genai


@dataclass
class APIKeyStatus:
    """Track status of an API key."""
    key: str
    last_used: float = 0
    request_count: int = 0
    last_error: Optional[str] = None
    is_rate_limited: bool = False
    rate_limit_until: float = 0


class APIKeyManager:
    """
    Manages multiple API keys with rotation and rate limit handling.
    
    Strategies:
    - Round-robin: Rotate through keys sequentially
    - Random: Pick random key (helps distribute load)
    - Least-used: Pick key with lowest request count
    """
    
    def __init__(self, api_keys: List[str] = None, strategy: str = "round_robin"):
        """
        Initialize with list of API keys.
        
        Args:
            api_keys: List of Gemini API keys. If None, loads from environment.
            strategy: Rotation strategy - "round_robin", "random", or "least_used"
        """
        self.keys: List[APIKeyStatus] = []
        self.strategy = strategy
        self.current_index = 0
        self._models_cache = {}  # Cache GenerativeModel instances
        
        # Load keys
        if api_keys:
            for key in api_keys:
                self.keys.append(APIKeyStatus(key=key.strip()))
        else:
            self._load_from_env()
        
        if not self.keys:
            raise ValueError("No API keys provided. Set GEMINI_API_KEY or GEMINI_API_KEYS in environment.")
    
    def _load_from_env(self):
        """Load API keys from environment variables."""
        # Check for multiple keys (comma-separated)
        multi_keys = os.environ.get("GEMINI_API_KEYS", "")
        if multi_keys:
            for key in multi_keys.split(","):
                if key.strip():
                    self.keys.append(APIKeyStatus(key=key.strip()))
        
        # Also check single key
        single_key = os.environ.get("GEMINI_API_KEY", "")
        if single_key and not any(k.key == single_key.strip() for k in self.keys):
            self.keys.append(APIKeyStatus(key=single_key.strip()))
    
    def get_next_key(self) -> APIKeyStatus:
        """Get the next available API key based on strategy."""
        now = time.time()
        
        # Filter out rate-limited keys
        available_keys = [
            k for k in self.keys 
            if not k.is_rate_limited or k.rate_limit_until < now
        ]
        
        # Reset rate limit status for keys past their limit time
        for key in self.keys:
            if key.is_rate_limited and key.rate_limit_until < now:
                key.is_rate_limited = False
        
        if not available_keys:
            # All keys rate limited, use the one that will be available soonest
            available_keys = sorted(self.keys, key=lambda k: k.rate_limit_until)
            wait_time = available_keys[0].rate_limit_until - now
            if wait_time > 0:
                time.sleep(min(wait_time, 60))  # Wait up to 60 seconds
        
        # Select based on strategy
        if self.strategy == "random":
            selected = random.choice(available_keys)
        elif self.strategy == "least_used":
            selected = min(available_keys, key=lambda k: k.request_count)
        else:  # round_robin (default)
            # Find next available key in rotation
            for _ in range(len(self.keys)):
                self.current_index = (self.current_index + 1) % len(self.keys)
                if self.keys[self.current_index] in available_keys:
                    selected = self.keys[self.current_index]
                    break
            else:
                selected = available_keys[0]
        
        selected.last_used = now
        selected.request_count += 1
        return selected
    
    def mark_rate_limited(self, key: APIKeyStatus, wait_seconds: int = 60):
        """Mark a key as rate limited."""
        key.is_rate_limited = True
        key.rate_limit_until = time.time() + wait_seconds
        key.last_error = "Rate limited"
    
    def get_model(self, model_name: str = "gemini-2.0-flash") -> tuple:
        """
        Get a configured GenerativeModel with rotated API key.
        
        Returns:
            Tuple of (model, key_status)
        """
        key_status = self.get_next_key()
        
        # Configure genai with this key
        genai.configure(api_key=key_status.key)
        
        # Create or get cached model
        cache_key = f"{key_status.key[:10]}:{model_name}"
        if cache_key not in self._models_cache:
            self._models_cache[cache_key] = genai.GenerativeModel(model_name)
        
        return self._models_cache[cache_key], key_status
    
    def get_stats(self) -> dict:
        """Get usage statistics for all keys."""
        return {
            "total_keys": len(self.keys),
            "available_keys": len([k for k in self.keys if not k.is_rate_limited]),
            "keys": [
                {
                    "key_prefix": k.key[:10] + "...",
                    "request_count": k.request_count,
                    "is_rate_limited": k.is_rate_limited,
                    "last_error": k.last_error
                }
                for k in self.keys
            ]
        }


# Global instance for convenience
_key_manager: Optional[APIKeyManager] = None


def get_key_manager() -> APIKeyManager:
    """Get or create the global API key manager."""
    global _key_manager
    if _key_manager is None:
        _key_manager = APIKeyManager()
    return _key_manager


def reset_key_manager():
    """Reset the global API key manager (useful for testing)."""
    global _key_manager
    _key_manager = None
