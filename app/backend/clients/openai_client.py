"""OpenAI client for ChatGPT enrichment with caching and schema validation."""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from config import settings
from db.models import ChatGPTCache


class OpenAIAnalysis(BaseModel):
    """Schema for ChatGPT analysis response."""
    symbol: str = Field(..., description="Stock symbol")
    fundamentals_summary: str = Field(..., description="1-2 sentence plain-English summary")
    catalysts: List[str] = Field(..., description="Top 3 catalysts")
    risks: List[str] = Field(..., description="Top 3 risks")
    earnings_date: str = Field(..., description="YYYY-MM-DD or 'unknown'")
    qualitative_score: float = Field(..., ge=0.0, le=1.0, description="Score between 0 and 1")
    
    @validator('earnings_date')
    def validate_earnings_date(cls, v):
        """Validate earnings date format."""
        if v == "unknown":
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError("earnings_date must be YYYY-MM-DD or 'unknown'")
    
    @validator('catalysts', 'risks')
    def validate_list_length(cls, v):
        """Validate list has exactly 3 items."""
        if len(v) != 3:
            raise ValueError("Must have exactly 3 items")
        return v


class OpenAIError(Exception):
    """Custom exception for OpenAI API errors."""
    pass


class OpenAIClient:
    """OpenAI client with caching and retry logic."""
    
    def __init__(self):
        if not settings.openai_enabled:
            raise ValueError("OpenAI is disabled in configuration")
        
        self.api_base = settings.openai_api_base
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def _make_request(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Make OpenAI API request with retry logic."""
        url = f"{self.api_base}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,  # Low temperature for consistent responses
            "max_tokens": 1000
        }
        
        try:
            response = await self.client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            if "error" in data:
                raise OpenAIError(f"OpenAI API error: {data['error']}")
            
            return data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limited - wait and retry
                await asyncio.sleep(2)
                raise
            raise OpenAIError(f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise OpenAIError(f"Request error: {str(e)}")
    
    async def analyze_stock(self, symbol: str, current_price: float, sector: str = None) -> OpenAIAnalysis:
        """Analyze a stock using ChatGPT."""
        system_prompt = """You are an analyst. Given a US equity ticker, return concise JSON assessing fundamentals and near-term catalysts/risks for a Wheel options strategy (selling cash-secured puts).

Return:
{
  "symbol": "TSCO",
  "fundamentals_summary": "1-2 sentence plain-English summary.",
  "catalysts": ["item1","item2","item3"],
  "risks": ["item1","item2","item3"],
  "earnings_date": "YYYY-MM-DD" | "unknown",
  "qualitative_score": 0.0-1.0
}

No prose, JSON only. Focus on factors relevant to selling cash-secured puts: company stability, sector trends, upcoming events, and overall risk profile."""

        user_prompt = f"Analyze {symbol} (current price: ${current_price:.2f}"
        if sector:
            user_prompt += f", sector: {sector}"
        user_prompt += ") for cash-secured put opportunities."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = await self._make_request(messages)
            content = response["choices"][0]["message"]["content"]
            
            # Parse JSON response
            try:
                analysis_data = json.loads(content)
                return OpenAIAnalysis(**analysis_data)
            except (json.JSONDecodeError, ValueError) as e:
                # Try to extract JSON from response if it's wrapped in prose
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        analysis_data = json.loads(json_match.group())
                        return OpenAIAnalysis(**analysis_data)
                    except (json.JSONDecodeError, ValueError):
                        pass
                
                # Return default analysis on parsing failure
                return OpenAIAnalysis(
                    symbol=symbol,
                    fundamentals_summary="Analysis unavailable",
                    catalysts=["Unknown", "Unknown", "Unknown"],
                    risks=["Unknown", "Unknown", "Unknown"],
                    earnings_date="unknown",
                    qualitative_score=0.5
                )
                
        except Exception as e:
            # Return default analysis on API failure
            return OpenAIAnalysis(
                symbol=symbol,
                fundamentals_summary="Analysis failed",
                catalysts=["Unknown", "Unknown", "Unknown"],
                risks=["Unknown", "Unknown", "Unknown"],
                earnings_date="unknown",
                qualitative_score=0.5
            )


class OpenAICacheManager:
    """Manages OpenAI response caching."""
    
    def __init__(self, db: Session):
        self.db = db
        self.client = None
        if settings.openai_enabled:
            self.client = OpenAIClient()
    
    def _generate_cache_key(self, symbol: str, date: str) -> str:
        """Generate cache key for symbol and date."""
        key_string = f"{symbol}_{date}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get_cached_analysis(self, symbol: str, date: str) -> Optional[OpenAIAnalysis]:
        """Get cached analysis if available and not expired."""
        cache_key = self._generate_cache_key(symbol, date)
        
        cached = self.db.query(ChatGPTCache).filter(
            ChatGPTCache.key_hash == cache_key,
            ChatGPTCache.ttl > datetime.utcnow()
        ).first()
        
        if cached:
            try:
                return OpenAIAnalysis(**cached.response_json)
            except (ValueError, KeyError):
                # Invalid cached data, remove it
                self.db.delete(cached)
                self.db.commit()
        
        return None
    
    def cache_analysis(self, symbol: str, date: str, analysis: OpenAIAnalysis, ttl_hours: int = 24):
        """Cache analysis with TTL."""
        cache_key = self._generate_cache_key(symbol, date)
        ttl = datetime.utcnow() + timedelta(hours=ttl_hours)
        
        # Remove existing cache entry if exists
        existing = self.db.query(ChatGPTCache).filter(
            ChatGPTCache.key_hash == cache_key
        ).first()
        
        if existing:
            self.db.delete(existing)
        
        # Create new cache entry
        cache_entry = ChatGPTCache(
            key_hash=cache_key,
            response_json=analysis.dict(),
            ttl=ttl
        )
        
        self.db.add(cache_entry)
        self.db.commit()
    
    async def get_or_create_analysis(self, symbol: str, current_price: float, sector: str = None) -> OpenAIAnalysis:
        """Get cached analysis or create new one."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Try to get from cache first
        cached = self.get_cached_analysis(symbol, today)
        if cached:
            return cached
        
        # If OpenAI is disabled, return default analysis
        if not settings.openai_enabled or not self.client:
            return OpenAIAnalysis(
                symbol=symbol,
                fundamentals_summary="OpenAI analysis disabled",
                catalysts=["Analysis disabled", "Analysis disabled", "Analysis disabled"],
                risks=["Analysis disabled", "Analysis disabled", "Analysis disabled"],
                earnings_date="unknown",
                qualitative_score=0.5
            )
        
        # Create new analysis
        analysis = await self.client.analyze_stock(symbol, current_price, sector)
        
        # Cache the result
        self.cache_analysis(symbol, today, analysis)
        
        return analysis
    
    def cleanup_expired_cache(self):
        """Remove expired cache entries."""
        expired = self.db.query(ChatGPTCache).filter(
            ChatGPTCache.ttl < datetime.utcnow()
        ).all()
        
        for entry in expired:
            self.db.delete(entry)
        
        self.db.commit()
        return len(expired)
