from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from typing import List, Optional

from app.models.dashboard import SessionStats


class Event(BaseModel):
    type: str
    data: Optional[dict] = None
    timestamp: Optional[datetime] = datetime.now().isoformat()

class SessionProgress(BaseModel):
    topic_id: Optional[int] = None
    module_id: Optional[int] = None
    phase_id: Optional[int] = None

class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    NOT_STARTED = "NOT_STARTED"

class Session(BaseModel):
    id: str
    user_id: str
    course_id: str
    progress: SessionProgress
    previous_response_id: Optional[str] = None
    # A phase is started from the checkpoint response id. This is so that the user can resume the lesson from a phase.
    checkpoint_response_id: Optional[str] = None
    status: Optional[SessionStatus] = None
    system_instructions: Optional[str] = None
    session_stats: Optional[SessionStats] = None
    created_at: Optional[datetime] = None
    event_logs: Optional[List[Event]] = []
    last_alive_timestamp: Optional[datetime] = None
