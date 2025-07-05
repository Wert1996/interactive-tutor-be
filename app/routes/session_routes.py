from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

from app.dao.db import Db
from app.models.session import Session, SessionStatus

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

class CreateSessionRequest(BaseModel):
    user_id: str
    course_id: str
    topic_id: Optional[int] = None
    module_id: Optional[int] = None
    phase_id: Optional[int] = None


@router.post("/", response_model=Session)
async def create_session(request: CreateSessionRequest):
    """
    Create a new learning session for a user and course.
    
    Args:
        request: Contains user_id and course_id
        
    Returns:
        SessionResponse: The created session object
    """
    db = Db.get_instance()
    
    # Validate that course exists
    if request.course_id not in db.courses:
        raise HTTPException(
            status_code=404, 
            detail=f"Course with id '{request.course_id}' not found"
        )
    
    if request.topic_id is None:
        request.topic_id = 0
    if request.module_id is None:
        request.module_id = 0

    # Generate unique session ID
    session_id = str(uuid.uuid4())
    
    # Create session object
    session = {
        "id": session_id,
        "user_id": request.user_id,
        "course_id": request.course_id,
        "created_at": datetime.utcnow().isoformat(),
        "status": SessionStatus.NOT_STARTED.value,
        "progress": {
            "topic_id": request.topic_id,
            "module_id": request.module_id,
            "phase_id": 0
        }
    }
    
    # Add session to sessions data
    db.update_session(session_id, session)
    
    return Session(**session)

@router.get("/{session_id}", response_model=Session)
async def get_session(session_id: str):
    """
    Get a session by its ID.
    
    Args:
        session_id: The ID of the session to retrieve
        
    Returns:
        SessionResponse: The session object
    """
    db = Db.get_instance()
    
    if session_id not in db.sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session with id '{session_id}' not found"
        )
    
    return Session(**db.sessions[session_id])

@router.get("/me")
async def get_my_sessions():
    """
    Get all sessions for the current user.
    """
    db = Db.get_instance()
    return db.sessions

@router.get("/")
async def list_sessions():
    """
    List all sessions.
    
    Returns:
        Dict: All sessions data
    """
    db = Db.get_instance()
    return db.sessions 