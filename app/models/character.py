from enum import Enum
from pydantic import BaseModel


class CharacterRole(str, Enum):
    TEACHER = "teacher"
    CLASSMATE = "classmate"


class Character(BaseModel):
    role: CharacterRole
    name: str
    image_url: str
    age: int
    gender: str
    voice_id: str
    # Description of the character's personality traits and attributes. Includes interests, hobbies, etc.
    personality: str = None
    # Description of the character's background, interesting anecdotes from their life, etc.
    background: str = None
    # Description of the world the character lives in.
    world_description: str = None
    # Personal life description. Includes family, friends, pets, daily life, etc.
    personal_life: str = None
