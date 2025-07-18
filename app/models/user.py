from pydantic import BaseModel

from app.models.dashboard import UserStats

class OnboardingData(BaseModel):
    interests: list[str]
    hobbies: list[str]
    preferredAnalogies: list[str]
    age: int

class User(BaseModel):
    id: str
    name: str
    onboarding_data: OnboardingData
    user_stats: UserStats