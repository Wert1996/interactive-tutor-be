"""
OpenAI resource module for AI completions and chat interactions.
"""
import logging
from typing import Dict, Any, Optional
import os

import openai
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logger = logging.getLogger(__name__)


class OpenAIService:
    """Singleton OpenAI service for chat completions and other AI features"""
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OpenAIService, cls).__new__(cls)
            cls._client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        return cls._instance
    
    @property
    def client(self):
        """Get the OpenAI client instance"""
        return self._client
    

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.APIError, openai.APIConnectionError, openai.RateLimitError))
    )
    async def create_response(
        self,
        message: str,
        model: str = None,
        previous_response_id: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        instructions: Optional[str] = None,
        response_schema: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ):
        """
        Create a response using OpenAI's API
        """
        if not model:
            model = "gpt-4o-mini"
        
        logger.info(f"Creating response with model: {model}")
        
        try:
            response = await self.client.responses.create(
                model=model,
                input=message,
                previous_response_id=previous_response_id,
                temperature=temperature,
                max_output_tokens=max_tokens,
                instructions=instructions,
                text=response_schema,
                stream=stream,
            )
            return response
        except Exception as e:
            logger.error(f"Error creating response: {e}")
            raise

# Create a singleton instance for easier imports
openai_service = OpenAIService()

async def create_response(
    message: str,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 10000,
    previous_response_id: Optional[str] = None,
    instructions: Optional[str] = None,
    response_schema: Optional[Dict[str, Any]] = None,
    stream: bool = False,
) -> Dict[str, Any]:
    """
    Create a response using OpenAI's API
    """
    response = await openai_service.create_response(
        message=message,
        model=model,
        previous_response_id=previous_response_id,
        temperature=temperature,
        max_tokens=max_tokens,
        instructions=instructions,
        response_schema=response_schema,
        stream=stream,
    )
    return response
