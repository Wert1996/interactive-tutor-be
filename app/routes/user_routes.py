import uuid
from fastapi import APIRouter
from pydantic import BaseModel
from app.dao.db import Db
from app.models.user import OnboardingData, User

router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("/", response_model=User)
async def create_user(request: User) -> User:
    db = Db.get_instance()
    user = User(id=request.id, name=request.name, onboarding_data=request.onboarding_data)
    db.create_user(request.id, user.model_dump())
    return user

@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str) -> User:
    db = Db.get_instance()
    user = db.get_user(user_id)
    return user
