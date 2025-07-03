import json
from typing import Dict, Any, Union, List
import logging
from datetime import datetime

from app.dao.db import Db
from app.models.course import Command, CommandType, ContentModule, Course, InstructionModule, MultipleChoiceQuestionPayload, PhaseType
from app.models.session import Session, SessionStatus
from app.resources.openai import create_response
from app.utils import prompts

logger = logging.getLogger(__name__)

class LearningInterface:
    def __init__(self):
        self.db = Db.get_instance()
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming WebSocket messages and return appropriate responses.
        """
        message_type = message.get("type", "unknown")
        
        try:
            if message_type == "ping":
                return await self._handle_ping(message)
            elif message_type == "start_session":
                return await self._handle_start_session(message)
            else:
                return {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                    "timestamp": datetime.now().isoformat()
                }   
        except Exception as e:
            logger.error(f"Error in process_message: {str(e)}")
            return {
                "type": "error",
                "message": f"Internal error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_ping(self, message: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "pong",
            "message": "Server is alive",
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_start_session(self, message: Dict[str, Any]) -> Dict[str, Any]:
        session_id = message.get("session_id", "")
        session_data = self.db.get_session(session_id)
        if not session_data:
            return {
                "type": "error",
                "message": f"Session with id {session_id} not found",
                "timestamp": datetime.now().isoformat()
            }
        course = self.db.get_course(session_data.course_id)
        if not course:
            return {
                "type": "error",
                "message": f"Course with id {session_data.get('course_id', '')} not found",
                "timestamp": datetime.now().isoformat()
            }
        return await self.start_phase(session_data, course)
    
    async def start_phase(self, session: Session, course: Course):
        phase_id = session.progress.phase_id if session.progress.phase_id is not None else 0
        phase = course.topics[session.progress.topic_id].modules[session.progress.module_id].phases[phase_id]
        session.progress.phase_id = phase_id
        system_instructions = None
        if session.status == SessionStatus.NOT_STARTED:
            system_instructions = prompts.learning_interface_system_prompt(course.description)
            session.status = SessionStatus.ACTIVE
            session.previous_response_id = None
            session.checkpoint_response_id = None
        else:
            session.previous_response_id = session.checkpoint_response_id
        self.db.update_session_in_memory(session.session_id, session.model_dump())
        phase_update_prompt = prompts.phase_update_prompt(phase.instruction, phase.content)
        if phase.type == PhaseType.CONTENT:
            self.execute_commands(phase.content)    
        response = await create_response(message=phase_update_prompt, instructions=system_instructions, previous_response_id=session.previous_response_id)
        content = await self.parse_response(response)
        return await self.execute_commands(content)
    
    async def parse_response(self, response):
        # This implementation is for the normal request-response flow. Streaming will be handled later.
        response_content = response.output_text
        # Parse commands in sequence: <TEACHER_SPEECH> <CLASSMATE_SPEECH> <WHITEBOARD> <DIAGRAM> <MCQ_QUESTION> <FINISH_MODULE>
        commands = []
        while response_content:
            if response_content.startswith("<FINISH_MODULE/>"):
                commands.append(Command(type=CommandType.FINISH_MODULE, payload={}))
                response_content = response_content[len("<FINISH_MODULE/>"):]
            elif response_content.startswith("<MCQ_QUESTION>"):
                mcq_question_start = response_content.find("</MCQ_QUESTION>")
                mcq_question_content = response_content[len("<MCQ_QUESTION>"):mcq_question_start]
                mcq_question_json = json.loads(mcq_question_content)
                mcq_question = MultipleChoiceQuestionPayload(**mcq_question_json)
                commands.append(Command(type=CommandType.MCQ_QUESTION, payload=mcq_question))
            elif response_content.startswith("<TEACHER_SPEECH>"):
                teacher_speech_start = response_content.find("</TEACHER_SPEECH>")
                teacher_speech_content = response_content[len("<TEACHER_SPEECH>"):teacher_speech_start]
                commands.append(Command(type=CommandType.TEACHER_SPEECH, payload={"text": teacher_speech_content}))
                response_content = response_content[teacher_speech_start + len("</TEACHER_SPEECH>"):]
            elif response_content.startswith("<CLASSMATE_SPEECH>"):
                classmate_speech_start = response_content.find("</CLASSMATE_SPEECH>")
                classmate_speech_content = response_content[len("<CLASSMATE_SPEECH>"):classmate_speech_start]
                commands.append(Command(type=CommandType.CLASSMATE_SPEECH, payload={"text": classmate_speech_content}))
                response_content = response_content[classmate_speech_start + len("</CLASSMATE_SPEECH>"):]
            elif response_content.startswith("<WHITEBOARD>"):
                whiteboard_start = response_content.find("</WHITEBOARD>")
                whiteboard_content = response_content[len("<WHITEBOARD>"):whiteboard_start]
                commands.append(Command(type=CommandType.WHITEBOARD, payload={"html": whiteboard_content}))
                response_content = response_content[whiteboard_start + len("</WHITEBOARD>"):]
        return commands
    
    async def execute_commands(self, commands: List[Command]):
        for command in commands:
            if command.type == CommandType.TEACHER_SPEECH:
                await self.execute_teacher_speech(command.payload)
            elif command.type == CommandType.CLASSMATE_SPEECH:
                await self.execute_classmate_speech(command.payload)
            elif command.type == CommandType.WHITEBOARD:
                await self.execute_whiteboard(command.payload)