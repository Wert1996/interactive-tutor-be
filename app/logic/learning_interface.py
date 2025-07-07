import asyncio
import json
import base64
from typing import Dict, Any, Union, List
import logging
from datetime import datetime
from fastapi import WebSocket

from app.dao.db import Db
from app.models.course import (
    AckPayload, BinaryChoiceQuestionPayload, Command, CommandType, Course, MultipleChoiceQuestionPayload, PhaseType,
    TeacherSpeechPayload, ClassmateSpeechPayload, WhiteboardPayload, WaitForStudentPayload
)
from app.models.session import Session, SessionStatus
from app.resources.elevenlabs import generate_speech
from app.resources.openai import create_response, transcribe_audio
from app.utils import prompts

logger = logging.getLogger(__name__)

class LearningInterface:
    def __init__(self, websocket: WebSocket):
        self.db = Db.get_instance()
        self.websocket = websocket
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming WebSocket messages and return appropriate responses.
        """
        message_type = message.get("type", "unknown")
        
        try:
            if message_type == "ping":
                await self._handle_ping(message)
            elif message_type == "start_session":
                await self._handle_start_session(message)
            elif message_type == "next_phase":
                await self._handle_next_phase(message)
            elif message_type == "student_interaction":
                await self._handle_student_interaction(message)
            else:
                await self.websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                    "timestamp": datetime.now().isoformat()
                })   
        except Exception as e:
            logger.error(f"Error in process_message: {str(e)}")
            await self.websocket.send_json({
                "type": "error",
                "message": f"Internal error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
    
    async def _handle_ping(self, message: Dict[str, Any]) -> Dict[str, Any]:
        await self.websocket.send_json({
            "type": "pong",
            "message": "Server is alive",
            "timestamp": datetime.now().isoformat()
        })
    
    async def _handle_start_session(self, message: Dict[str, Any]) -> Dict[str, Any]:
        session_id = message.get("session_id", "")
        session_data = self.db.get_session(session_id)
        if not session_data:
            await self.websocket.send_json({
                "type": "error",
                "message": f"Session with id {session_id} not found",
                "timestamp": datetime.now().isoformat()
            })
            return
        course = self.db.get_course(session_data.course_id)
        if not course:
            await self.websocket.send_json({
                "type": "error",
                "message": f"Course with id {session_data.get('course_id', '')} not found",
                "timestamp": datetime.now().isoformat()
            })
            return
        await self.start_phase(session_data, course)
    
    def progress_to_next_phase(self, session: Session, course: Course):
        phase_id = session.progress.phase_id
        topic_id = session.progress.topic_id
        topic = course.topics[topic_id]
        module_id = session.progress.module_id
        module = topic.modules[module_id]
        if phase_id < len(module.phases) - 1:
            session.progress.phase_id = phase_id + 1
            return True
        if module_id < len(topic.modules) - 1:
            session.progress.module_id = module_id + 1
            session.progress.phase_id = 0
            return True
        if topic_id < len(course.topics) - 1:
            session.progress.topic_id = topic_id + 1
            session.progress.module_id = 0
            session.progress.phase_id = 0
            return True
        return False

    async def _handle_next_phase(self, message: Dict[str, Any]) -> Dict[str, Any]:
        session_id = message.get("session_id", "")
        session = self.db.get_session(session_id)
        if not session:
            await self.websocket.send_json({
                "type": "error",
                "message": f"Session with id {session_id} not found",
            })
            return
        course = self.db.get_course(session.course_id)
        if not course:
            await self.websocket.send_json({
                "type": "error",
                "message": f"Course with id {session.course_id} not found",
            })
            return
        if not self.progress_to_next_phase(session, course):
            await self.finish_module(session, course)
        else:
            session.checkpoint_response_id = session.previous_response_id
            self.db.update_session_in_memory(session.id, session.model_dump())
            await self.start_phase(session, course)

    async def _handle_student_interaction(self, message: Dict[str, Any]) -> Dict[str, Any]:
        session_id = message.get("session_id", "")
        session = self.db.get_session(session_id)
        if not session:
            await self.websocket.send_json({
                "type": "error",
                "message": f"Session with id {session_id} not found",
            })
            return
        course = self.db.get_course(session.course_id)
        if not course:
            await self.websocket.send_json({
                "type": "error",
                "message": f"Course with id {session.course_id} not found",
            })
            return
        interaction = message.get("interaction", {})
        if interaction.get("type") == "speech":
            audio_bytes = interaction.get("audio_bytes", None)
            text = await transcribe_audio(audio_bytes)
            if text:
                text = f"Student has said something. Please respond accordingly. Use the commands to respond. The following is what the student said: {text}\nEmit <FINISH_MODULE/> at the end if the student's query is answered and the phase is complete."
                model_response =  await create_response(message=text, previous_response_id=session.previous_response_id)
                session.previous_response_id = model_response.id
                self.db.update_session_in_memory(session.id, session.model_dump())
                await self.execute_commands(await self.parse_response(model_response))
        elif interaction.get("type") in ["mcq_question", "binary_choice_question"]:
            text = f"Student answered {'correctly' if interaction.get('correct', False) else 'incorrectly'}. Student's answer: {interaction.get('answer', '')}. Explain the answer if needed. Use only the defined commands, and no other command. If something is to be explained, use TEACHER_SPEECH and other defined commands. Emit FINISH_MODULE if we can proceed."
            model_response =  await create_response(message=text, previous_response_id=session.previous_response_id)
            session.previous_response_id = model_response.id
            self.db.update_session_in_memory(session.id, session.model_dump())
            await self.execute_commands(await self.parse_response(model_response))
        else:
            await self.websocket.send_json({
                "type": "error",
                "message": "Unknown message type",
            })

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
        self.db.update_session_in_memory(session.id, session.model_dump())
        content_string = "".join([cmd.to_string() for cmd in phase.content]) if phase.content else None
        phase_update_prompt = prompts.phase_update_prompt(content_string, phase.instruction)
        if phase.type == PhaseType.CONTENT:
            await self.execute_commands(phase.content)  
        if system_instructions:  
            response = await create_response(message=phase_update_prompt, instructions=system_instructions, previous_response_id=session.previous_response_id)
        else:
            response = await create_response(message=phase_update_prompt, previous_response_id=session.previous_response_id)
        session.previous_response_id = response.id
        self.db.update_session_in_memory(session.id, session.model_dump())
        content = await self.parse_response(response)
        await self.execute_commands(content)
    
    async def finish_module(self, session: Session, course: Course):
        session.status = SessionStatus.COMPLETED
        self.db.update_session(session.id, session.model_dump())
        # Can add some personalised feedback and messages here.
        await self.websocket.send_json({
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
            elif response_content.startswith("<ACKNOWLEDGE/>"):
                commands.append(Command(command_type=CommandType.ACKNOWLEDGE, payload=AckPayload()))
                response_content = response_content[len("<ACKNOWLEDGE/>"):]
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
            elif response_content.startswith("<BINARY_CHOICE_QUESTION>"):
                binary_choice_question_start = response_content.find("</BINARY_CHOICE_QUESTION>")
                binary_choice_question_content = response_content[len("<BINARY_CHOICE_QUESTION>"):binary_choice_question_start]
                binary_choice_question_json = json.loads(binary_choice_question_content)
                binary_choice_question = BinaryChoiceQuestionPayload(**binary_choice_question_json)
                commands.append(Command(command_type=CommandType.BINARY_CHOICE_QUESTION, payload=binary_choice_question))
                response_content = response_content[binary_choice_question_start + len("</BINARY_CHOICE_QUESTION>"):]
            else:
                # Skip unknown content
                response_content = response_content[1:]
        return commands
    
    async def execute_commands(self, commands: List[Command]):
        for command in commands:
            try:
                if command.command_type == CommandType.TEACHER_SPEECH:
                    audio_bytes = await generate_speech(command.payload.text, "VD1if7jDVYtAKs4P0FIY")
                    # Encode audio bytes to base64 string
                    command.payload.audio_bytes = base64.b64encode(audio_bytes).decode('utf-8')
                elif command.command_type == CommandType.CLASSMATE_SPEECH:
                    audio_bytes = await generate_speech(command.payload.text, "f2yUVfK5jdm78zlpcZ8C")
                    # Encode audio bytes to base64 string
                    command.payload.audio_bytes = base64.b64encode(audio_bytes).decode('utf-8')
                        
                await self.websocket.send_json({
                    "type": "command",
                    "command": command.model_dump()
                })
            except Exception as e:
                logger.error(f"Error executing command {command.command_type}: {str(e)}")
                await self.websocket.send_json({
                    "type": "error",
                    "message": f"Error executing command: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })