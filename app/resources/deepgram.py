from functools import cache
import os
from deepgram import PrerecordedOptions, DeepgramClient


"""
Transcription:
from deepgram import PrerecordedOptions

response = deepgram.listen.rest.v("1").transcribe_file_async(
    source=open("path/to/your/audio.wav", "rb"),
    callback_url="https://your-callback-url.com/webhook",
    options=PrerecordedOptions(model="nova-3") # Apply other options
)
"""
class DeepgramResource:
    _instance = None
    _deepgram = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DeepgramResource, cls).__new__(cls)
            cls._deepgram = DeepgramClient(api_key=os.environ.get("DEEPGRAM_API_KEY"))
        return cls._instance
    
    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        response = await self._deepgram.listen.rest.v("1").transcribe_file_async(
            source=audio_bytes,
                options=PrerecordedOptions(model="nova-3")
            )
        return response.results.channels[0].alternatives[0].transcript

deepgram_resource = DeepgramResource()

@cache
async def transcribe_audio(audio_bytes: bytes):
    return await deepgram_resource.transcribe_audio(audio_bytes)
