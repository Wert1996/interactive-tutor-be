import uuid
from fastapi import APIRouter
from pydantic import BaseModel
from app.dao.db import Db
from app.models.dashboard import Dashboard

router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])


@router.get("/{user_id}", response_model=Dashboard)
async def get_dashboard(user_id: str) -> Dashboard:
    db = Db.get_instance()
    dashboard = db.get_dashboard(user_id)
    return dashboard
