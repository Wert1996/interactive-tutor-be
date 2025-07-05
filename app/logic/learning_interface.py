import asyncio
import json
import base64
from typing import Dict, Any, Union, List
import logging
from datetime import datetime

from app.dao.db import Db
from app.models.course import (
    Command, CommandType, Course, MultipleChoiceQuestionPayload, PhaseType,
    TeacherSpeechPayload, ClassmateSpeechPayload, WhiteboardPayload, WaitForStudentPayload
)
from app.models.session import Session, SessionStatus
from app.resources.elevenlabs import generate_speech
from app.resources.openai import create_response, transcribe_audio
from app.utils import prompts

logger = logging.getLogger(__name__)

class LearningInterface:
    def __init__(self):
        self.db = Db.get_instance()
    
    async def process_message(self, message: Dict[str, Any], client_buffer: asyncio.Queue) -> Dict[str, Any]:
        """
        Process incoming WebSocket messages and return appropriate responses.
        """
        message_type = message.get("type", "unknown")
        
        try:
            if message_type == "ping":
                await self._handle_ping(message, client_buffer)
            elif message_type == "start_session":
                await self._handle_start_session(message, client_buffer)
            elif message_type == "next_phase":
                await self._handle_next_phase(message, client_buffer)
            elif message_type == "student_interaction":
                await self._handle_student_interaction(message, client_buffer)
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
    
    async def _handle_ping(self, message: Dict[str, Any], client_buffer: asyncio.Queue) -> Dict[str, Any]:
        await client_buffer.put({
            "type": "pong",
            "message": "Server is alive",
            "timestamp": datetime.now().isoformat()
        })
    
    async def _handle_start_session(self, message: Dict[str, Any], client_buffer: asyncio.Queue) -> Dict[str, Any]:
        session_id = message.get("session_id", "")
        session_data = self.db.get_session(session_id)
        if not session_data:
            await client_buffer.put({
                "type": "error",
                "message": f"Session with id {session_id} not found",
                "timestamp": datetime.now().isoformat()
            })
            return
        course = self.db.get_course(session_data.course_id)
        if not course:
            await client_buffer.put({
                "type": "error",
                "message": f"Course with id {session_data.get('course_id', '')} not found",
                "timestamp": datetime.now().isoformat()
            })
            return
        await self.start_phase(session_data, course, client_buffer)
    
    async def _handle_next_phase(self, message: Dict[str, Any], client_buffer: asyncio.Queue) -> Dict[str, Any]:
        session_id = message.get("session_id", "")
        session = self.db.get_session(session_id)
        if not session:
            await client_buffer.put({
                "type": "error",
                "message": f"Session with id {session_id} not found",
            })
            return
        course = self.db.get_course(session.course_id)
        if not course:
            await client_buffer.put({
                "type": "error",
                "message": f"Course with id {session.course_id} not found",
            })
            return
        phase_id = session.progress.phase_id
        module = course.topics[session.progress.topic_id].modules[session.progress.module_id]
        if phase_id == len(module.phases) - 1:
            await self.finish_module(session, course, client_buffer)
        else:
            session.checkpoint_response_id = session.previous_response_id
            session.progress.phase_id = phase_id + 1
            self.db.update_session_in_memory(session.id, session.model_dump())
            await self.start_phase(session, course, client_buffer)

    async def _handle_student_interaction(self, message: Dict[str, Any], client_buffer: asyncio.Queue) -> Dict[str, Any]:
        session_id = message.get("session_id", "")
        session = self.db.get_session(session_id)
        if not session:
            await client_buffer.put({
                "type": "error",
                "message": f"Session with id {session_id} not found",
            })
            return
        course = self.db.get_course(session.course_id)
        if not course:
            await client_buffer.put({
                "type": "error",
                "message": f"Course with id {session.course_id} not found",
            })
            return
        if message.get("type") == "speech":
            audio_bytes = message.get("audio_bytes", None)
            text = await transcribe_audio(audio_bytes)
            if text:
                text = f"Student said: {text}"
                model_response =  await create_response(message=text, previous_response_id=session.previous_response_id)
                session.previous_response_id = model_response.id
                self.db.update_session_in_memory(session.id, session.model_dump())
                await self.execute_commands(self.parse_response(model_response), client_buffer)
        elif message.get("type") == "mcq_question":
            mcq_question = message.get("mcq_question", None)
            if mcq_question:
                text = f"Student answered: {mcq_question.answer}"
                model_response =  await create_response(message=text, previous_response_id=session.previous_response_id)
                session.previous_response_id = model_response.id
                self.db.update_session_in_memory(session.id, session.model_dump())
                await self.execute_commands(self.parse_response(model_response), client_buffer)
        else:
            await client_buffer.put({
                "type": "error",
                "message": "Unknown message type",
            })

    async def start_phase(self, session: Session, course: Course, client_buffer: asyncio.Queue):
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
        self.db.update_session_in_memory(session.id, session.model_dump())
        phase_update_prompt = prompts.phase_update_prompt(phase.instruction, phase.content)
        if phase.type == PhaseType.CONTENT:
            await self.execute_commands(phase.content, client_buffer)    
        response = await create_response(message=phase_update_prompt, instructions=system_instructions, previous_response_id=session.previous_response_id)
        session.previous_response_id = response.id
        self.db.update_session_in_memory(session.id, session.model_dump())
        content = await self.parse_response(response)
        await self.execute_commands(content, client_buffer)
    
    async def finish_module(self, session: Session, course: Course, client_buffer: asyncio.Queue):
        session.status = SessionStatus.COMPLETED
        self.db.update_session(session.id, session.model_dump())
        # Can add some personalised feedback and messages here.
        await client_buffer.put({
            "type": "finish_module",
            "message": "Module finished",
        })

    async def parse_response(self, response):
        # This implementation is for the normal request-response flow. Streaming will be handled later.
        response_content = response.output_text
        # Parse commands in sequence: <TEACHER_SPEECH> <CLASSMATE_SPEECH> <WHITEBOARD> <DIAGRAM> <MCQ_QUESTION> <FINISH_MODULE>
        commands = []
        while response_content:
            if response_content.startswith("<FINISH_MODULE/>"):
                commands.append(Command(command_type=CommandType.FINISH_MODULE, payload=WaitForStudentPayload()))
                response_content = response_content[len("<FINISH_MODULE/>"):]
            elif response_content.startswith("<MCQ_QUESTION>"):
                mcq_question_start = response_content.find("</MCQ_QUESTION>")
                mcq_question_content = response_content[len("<MCQ_QUESTION>"):mcq_question_start]
                mcq_question_json = json.loads(mcq_question_content)
                mcq_question = MultipleChoiceQuestionPayload(**mcq_question_json)
                commands.append(Command(command_type=CommandType.MCQ_QUESTION, payload=mcq_question))
                response_content = response_content[mcq_question_start + len("</MCQ_QUESTION>"):]
            elif response_content.startswith("<TEACHER_SPEECH>"):
                teacher_speech_start = response_content.find("</TEACHER_SPEECH>")
                teacher_speech_content = response_content[len("<TEACHER_SPEECH>"):teacher_speech_start]
                teacher_speech_payload = TeacherSpeechPayload(text=teacher_speech_content)
                commands.append(Command(command_type=CommandType.TEACHER_SPEECH, payload=teacher_speech_payload))
                response_content = response_content[teacher_speech_start + len("</TEACHER_SPEECH>"):]
            elif response_content.startswith("<CLASSMATE_SPEECH>"):
                classmate_speech_start = response_content.find("</CLASSMATE_SPEECH>")
                classmate_speech_content = response_content[len("<CLASSMATE_SPEECH>"):classmate_speech_start]
                classmate_speech_payload = ClassmateSpeechPayload(text=classmate_speech_content)
                commands.append(Command(command_type=CommandType.CLASSMATE_SPEECH, payload=classmate_speech_payload))
                response_content = response_content[classmate_speech_start + len("</CLASSMATE_SPEECH>"):]
            elif response_content.startswith("<WHITEBOARD>"):
                whiteboard_start = response_content.find("</WHITEBOARD>")
                whiteboard_content = response_content[len("<WHITEBOARD>"):whiteboard_start]
                whiteboard_payload = WhiteboardPayload(html=whiteboard_content)
                commands.append(Command(command_type=CommandType.WHITEBOARD, payload=whiteboard_payload))
                response_content = response_content[whiteboard_start + len("</WHITEBOARD>"):]
            else:
                # Skip unknown content
                response_content = response_content[1:]
        return commands
    
    async def execute_commands(self, commands: List[Command], client_buffer: asyncio.Queue):
        for command in commands:
            try:
                if command.command_type == CommandType.TEACHER_SPEECH:
                    # Ensure we have a TeacherSpeechPayload object
                    if isinstance(command.payload, TeacherSpeechPayload):
                        audio_bytes = await generate_speech(command.payload.text, "VD1if7jDVYtAKs4P0FIY")
                        # Encode audio bytes to base64 string
                        command.payload.audio_bytes = base64.b64encode(audio_bytes).decode('utf-8')
                elif command.command_type == CommandType.CLASSMATE_SPEECH:
                    # Ensure we have a ClassmateSpeechPayload object
                    if isinstance(command.payload, ClassmateSpeechPayload):
                        audio_bytes = await generate_speech(command.payload.text, "pPdl9cQBQq4p6mRkZy2Z")
                        # Encode audio bytes to base64 string
                        command.payload.audio_bytes = base64.b64encode(audio_bytes).decode('utf-8')
                        
                await client_buffer.put({
                    "type": "command",
                    "command": command.model_dump()
                })
            except Exception as e:
                logger.error(f"Error executing command {command.command_type}: {str(e)}")
                await client_buffer.put({
                    "type": "error",
                    "message": f"Error executing command: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })