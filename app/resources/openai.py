"""
OpenAI resource module for AI completions and chat interactions.
"""
import base64
from functools import cache
import logging
from typing import Dict, Any, Optional
import os
import io

import openai
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logger = logging.getLogger(__name__)


class OpenAIResource:
    """Singleton OpenAI service for chat completions and other AI features"""
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OpenAIResource, cls).__new__(cls)
            cls._client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        return cls._instance
    
    @property
    def client(self):
        """Get the OpenAI client instance"""
        return self._client
    
    async def transcribe_audio(self, audio_bytes: bytes):
        """Transcribe audio using OpenAI's API"""
        # Create a file-like object with proper audio format
        if audio_bytes:
            # If audio_bytes is base64 encoded, decode it first
            if isinstance(audio_bytes, str):
                audio_bytes = base64.b64decode(audio_bytes)
        else:
            return None
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"  # Set a default audio format
        
        response = await self.client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
        return response.text

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
            model = "gpt-4o"
        try:
            # Ignore parameters that are None
            # Build kwargs dict, omitting any that are None
            params = {
                "model": model,
                "input": message,
                "previous_response_id": previous_response_id,
                "temperature": temperature,
                "max_output_tokens": max_tokens,
                "instructions": instructions,
                "text": response_schema,
                "stream": stream,
            }
            # Remove keys where value is None
            params = {k: v for k, v in params.items() if v is not None}
            response = await self.client.responses.create(**params)
            return response
        except Exception as e:
            logger.error(f"Error creating response: {e}")
            raise

# Create a singleton instance for easier imports
openai_resource = OpenAIResource()

async def transcribe_audio(audio_bytes: bytes):
    """Transcribe audio using OpenAI's API"""
    response = await openai_resource.transcribe_audio(audio_bytes)
    return response

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
    response = await openai_resource.create_response(
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
