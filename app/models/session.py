from enum import Enum
from pydantic import BaseModel
from typing import Optional

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
