import os
from elevenlabs.client import AsyncElevenLabs


class ElevenLabsResource:
    _instance = None
    _eleven = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ElevenLabsResource, cls).__new__(cls)
            cls._eleven = AsyncElevenLabs(api_key=os.environ.get("ELEVENLABS_API_KEY"))
        return cls._instance
    
    @property
    def client(self):
        return self._eleven
    
    async def generate_speech(self, text: str, voice_id: str):
        return self._eleven.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )

elevenlabs_resource = ElevenLabsResource()

async def generate_speech(text: str, voice_id: str):
    async_iterator = await elevenlabs_resource.generate_speech(text, voice_id)
    audio_bytes = b""
    async for chunk in async_iterator:
        audio_bytes += chunk
    return audio_bytes
