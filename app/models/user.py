from pydantic import BaseModel

class OnboardingData(BaseModel):
    interests: list[str]
    hobbies: list[str]
    preferredAnalogies: list[str]
    age: int

class User(BaseModel):
    id: str
    name: str
    onboarding_data: OnboardingData
