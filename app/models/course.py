from pydantic import BaseModel
from typing import List, Optional, Union, Dict, Any
from enum import Enum


class CommandType(str, Enum):
    TEACHER_SPEECH = "TEACHER_SPEECH"
    CLASSMATE_SPEECH = "CLASSMATE_SPEECH"
    WHITEBOARD = "WHITEBOARD"
    QUESTION = "QUESTION"
    MCQ_QUESTION = "MCQ_QUESTION"
    BINARY_CHOICE_QUESTION = "BINARY_CHOICE_QUESTION"
    WAIT_FOR_STUDENT = "WAIT_FOR_STUDENT"
    FINISH_MODULE = "FINISH_MODULE"
    ACKNOWLEDGE = "ACKNOWLEDGE"
    GAME = "GAME"

class PhaseType(str, Enum):
    CONTENT = "content"
    INSTRUCTION = "instruction"

class TeacherSpeechPayload(BaseModel):
    text: str
    audio_bytes: Optional[str] = None  # Base64 encoded audio data


class ClassmateSpeechPayload(BaseModel):
    text: str
    audio_bytes: Optional[str] = None  # Base64 encoded audio data


class WhiteboardPayload(BaseModel):
    html: str

class QuestionOption(BaseModel):
    text: str
    correct: bool

class MultipleChoiceQuestionPayload(BaseModel):
    question: str
    options: List[QuestionOption]

class BinaryChoiceQuestionPayload(BaseModel):
    question: str
    left: str
    right: str
    # correct is either "left" or "right"
    correct: str 

class GamePayload(BaseModel):
    game_id: str
    code: Optional[str] = None

class WaitForStudentPayload(BaseModel):
    pass

class AckPayload(BaseModel):
    pass

class Command(BaseModel):
    command_type: CommandType
    payload: Union[
        TeacherSpeechPayload,
        ClassmateSpeechPayload,
        WhiteboardPayload, 
        MultipleChoiceQuestionPayload,
        BinaryChoiceQuestionPayload,
        WaitForStudentPayload,
        AckPayload,
        GamePayload,
        Dict[str, Any]
    ]
    
    def to_string(self):
        if self.command_type == CommandType.TEACHER_SPEECH:
            return f"<TEACHER_SPEECH>{self.payload.text}</TEACHER_SPEECH>"
        elif self.command_type == CommandType.CLASSMATE_SPEECH:
            return f"<CLASSMATE_SPEECH>{self.payload.text}</CLASSMATE_SPEECH>"
        elif self.command_type == CommandType.WHITEBOARD:
            return f"<WHITEBOARD>{self.payload.html}</WHITEBOARD>"
        elif self.command_type == CommandType.MCQ_QUESTION:
            return f"<MCQ_QUESTION>{self.payload.model_dump_json()}</MCQ_QUESTION>"
        elif self.command_type == CommandType.BINARY_CHOICE_QUESTION:
            return f"<BINARY_CHOICE_QUESTION>{self.payload.model_dump_json()}</BINARY_CHOICE_QUESTION>"
        elif self.command_type == CommandType.WAIT_FOR_STUDENT:
            return f"<WAIT_FOR_STUDENT/>"
        elif self.command_type == CommandType.FINISH_MODULE:
            return f"<FINISH_MODULE/>"
        elif self.command_type == CommandType.ACKNOWLEDGE:
            return f"<ACKNOWLEDGE/>"
        elif self.command_type == CommandType.GAME:
            return f"<GAME>{self.payload.game_id}</GAME>"

class Phase(BaseModel):
    type: PhaseType
    content: Optional[List[Command]] = None
    instruction: Optional[str] = None


class Module(BaseModel):
    title: str
    description: str
    phases: Optional[List[Phase]] = None


class CourseTopic(BaseModel):
    title: str
    description: str
    modules: Optional[List[Module]] = None

class CourseStats(BaseModel):
    total_topics: int
    total_modules: int
    total_phases: int

class Course(BaseModel):
    id: str
    title: str
    description: str
    category: str
    estimatedDuration: str
    topics: Optional[List[CourseTopic]] = None
    stats: Optional[CourseStats] = None


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
    topics: Optional[List[CourseTopic]] = None


class UpdateCourseRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    estimatedDuration: Optional[str] = None
    instructor: Optional[str] = None
    topics: Optional[List[CourseTopic]] = None 