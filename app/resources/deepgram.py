import base64
from functools import cache
import io
import os
from deepgram import PrerecordedOptions, DeepgramClient, FileSource


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
        if audio_bytes:
        # If audio_bytes is base64 encoded, decode it first
            if isinstance(audio_bytes, str):
                audio_bytes = base64.b64decode(audio_bytes)
        else:
            return None
        payload: FileSource = {
            "buffer": audio_bytes,
        }

        response = await self._deepgram.listen.asyncrest.v("1").transcribe_file(
            source=payload,
            options=PrerecordedOptions(model="nova-3", punctuate=True,
                diarize=True, language="en-US"
            )
        )
        return response.results.channels[0].alternatives[0].transcript


deepgram_resource = DeepgramResource()


async def transcribe_audio(audio_bytes: bytes):
    return await deepgram_resource.transcribe_audio(audio_bytes)
