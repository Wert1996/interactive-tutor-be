from typing import List
import uuid
from fastapi import APIRouter
from pydantic import BaseModel
from app.dao.db import Db
from app.models.character import Character

router = APIRouter(prefix="/api/characters", tags=["characters"])


@router.get("/all", response_model=List[Character])
async def get_all_characters() -> List[Character]:
    db = Db.get_instance()
    characters = db.get_all_characters()
    return characters


@router.get("/{character_name}", response_model=Character)
async def get_character(character_name: str) -> Character:
    db = Db.get_instance()
    character = db.get_characters_by_names([character_name])[0]
    return character
