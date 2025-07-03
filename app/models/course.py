from pydantic import BaseModel
from typing import List, Optional, Union, Dict, Any
from enum import Enum


class CommandType(str, Enum):
    TEACHER_SPEECH = "TEACHER_SPEECH"
    CLASSMATE_SPEECH = "CLASSMATE_SPEECH"
    WHITEBOARD = "WHITEBOARD"
    QUESTION = "QUESTION"
    WAIT_FOR_STUDENT = "WAIT_FOR_STUDENT"


class PhaseType(str, Enum):
    CONTENT = "content"
    INSTRUCTION = "instruction"

class TeacherSpeechPayload(BaseModel):
    text: str
    audio_bytes: Optional[bytes] = None


class ClassmateSpeechPayload(BaseModel):
    text: str
    audio_bytes: Optional[bytes] = None


class WhiteboardPayload(BaseModel):
    html: str

class QuestionOption(BaseModel):
    text: str
    correct: bool

class MultipleChoiceQuestionPayload(BaseModel):
    question: str
    options: List[QuestionOption]


class WaitForStudentPayload(BaseModel):
    pass


class Command(BaseModel):
    command_type: CommandType
    payload: Union[
        TeacherSpeechPayload,
        ClassmateSpeechPayload,
        WhiteboardPayload, 
        MultipleChoiceQuestionPayload,
        WaitForStudentPayload,
        Dict[str, Any]
    ]

class Phase(BaseModel):
    type: PhaseType
    content: Optional[List[Command]] = None
    instruction: Optional[str] = None


class Module(BaseModel):
    title: str
    description: str
    phases: List[Phase]


class CourseTopic(BaseModel):
    title: str
    description: str
    modules: List[Module]

class Course(BaseModel):
    id: str
    title: str
    description: str
    category: str
    estimatedDuration: str
    topics: List[CourseTopic]


class CreateCourseRequest(BaseModel):
    title: str
    description: str
    category: str
    estimatedDuration: str
    instructor: str
    topics: List[CourseTopic] = []


class CourseResponse(BaseModel):
    id: str
    title: str
    description: str
    category: str
    estimatedDuration: str
    instructor: str
    topics: List[CourseTopic]


class UpdateCourseRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    estimatedDuration: Optional[str] = None
    instructor: Optional[str] = None
    topics: Optional[List[CourseTopic]] = None 