import asyncio
import json
import base64
from typing import Dict, Any, Optional, Union, List
import logging
from datetime import datetime
from fastapi import WebSocket

from app.dao.db import Db
from app.logic.command_parser import CommandParser
from app.logic.dashboard import DashboardBuilder
from app.models.character import Character
from app.models.course import (
    AckPayload, BinaryChoiceQuestionPayload, ClassmatePointPayload, Command, CommandType, Course, MultipleChoiceQuestionPayload, PhaseType, StudentPointPayload,
    TeacherSpeechPayload, ClassmateSpeechPayload, TwoPlayerGamePayload, WhiteboardPayload, WaitForStudentPayload, GamePayload
)
from app.models.session import Event, Session, SessionStatus
from app.resources.elevenlabs import create_speech_stream
from app.resources.openai import create_response
from app.resources.deepgram import transcribe_audio
from app.utils import prompts

logger = logging.getLogger(__name__)

class LearningInterface:
    def __init__(self, websocket: WebSocket):
        self.db = Db.get_instance()
        self.websocket = websocket
    
    def log_event(self, session: Session, event_type: str, data: Optional[dict] = None):
        session.event_logs.append(Event(type=event_type, data=data, timestamp=datetime.now().isoformat()))
        self.db.update_session_in_memory(session.id, session.model_dump())

    """
    Validate and sanitize the session
    """
    def validate_inputs(self, session_id: str):
        session_data = self.db.get_session(session_id)
        if not session_data:
            raise ValueError(f"Session with id {session_id} not found")
        course = self.db.get_course(session_data.course_id)
        if not course:
            raise ValueError(f"Course with id {session_data.course_id} not found")
        characters = self.db.get_characters_by_names([session_data.teacher.name, session_data.classmate.name])
        if not characters:
            raise ValueError(f"Teacher or classmate characters '{session_data.teacher} or {session_data.classmate}' not found")
        return session_data, course, characters

    async def handle_error(self, session_data: Session, error_message: str):
        await self.websocket.send_json({
            "type": "error",
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        })
        if session_data:
            self.log_event(session_data, "error", {"message": error_message})

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
            elif message_type == "start_two_player_game":
                await self._handle_two_player_game(message)
            elif message_type == "finish_two_player_game":
                await self._handle_finish_two_player_game(message)
            else:
                await self.handle_error(None, f"Unknown message type: {message_type}")
        except Exception as e:
            logger.error(f"Error in process_message: {str(e)}")
            await self.handle_error(None, f"Internal error: {str(e)}")
    
    async def _handle_ping(self, message: Dict[str, Any]) -> Dict[str, Any]:
        session_id = message.get("session_id", "")
        session, _, _ = self.validate_inputs(session_id)
        self.log_event(session, "ping", {})
        await self.websocket.send_json({
            "type": "pong",
            "message": "Server is alive",
            "timestamp": datetime.now().isoformat()
        })
    
    async def _handle_start_session(self, message: Dict[str, Any]) -> Dict[str, Any]:
        session_id = message.get("session_id", "")
        session_data, course, characters = self.validate_inputs(session_id)
        self.log_event(session_data, "start_session", {})
        await self.start_phase(session_data, course, characters)
    
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
        session, course, characters = self.validate_inputs(session_id)
        if not self.progress_to_next_phase(session, course):
            await self.finish_module(session, course)
        else:
            session.checkpoint_response_id = session.previous_response_id
            await self.start_phase(session, course, characters)

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
                interaction["transcription"] = text
                await self.websocket.send_json({
                    "type": "student_speech",
                    "text": text
                })
                text = f"Student has said something. Please respond accordingly. Use the commands to respond. Feel free to use whiteboard/teacher/classmate speech and other commands. If required, use the student's information to make the session more engaging and personalized. Use analogies that the student can relate to, using the student's information. Stick to the information provided by the student. The following is what the student said: {text}\nEmit <FINISH_MODULE/> at the end if the student's query is answered and the main part of this phase is complete."
                await self.create_response_and_execute(
                    {
                        "message": text,
                        "instructions": session.system_instructions,
                        "previous_response_id": session.previous_response_id
                    },
                    session
                )
                self.log_event(session, "student_interaction", {"interaction": interaction})
        elif interaction.get("type") in ["mcq_question", "binary_choice_question"]:
            text = f"Student answered {'correctly' if interaction.get('correct', False) else 'incorrectly'}. Student's answer: {interaction.get('answer', '')}. Explain the answer if needed. Use only the defined commands, and no other command. If something is to be explained, use TEACHER_SPEECH and other defined commands. Feel free to use whiteboard/teacher/classmate speech and other commands. Emit <FINISH_MODULE/> command at the end so that we can proceed. Do not overcomplicate this, and emit FINISH_MODULE to proceed further."
            await self.create_response_and_execute(
                {
                    "message": text,
                    "instructions": session.system_instructions,
                    "previous_response_id": session.previous_response_id
                },
                session
            )
            self.log_event(session, "student_interaction", {"interaction": interaction})
        else:
            await self.websocket.send_json({
                "type": "error",
                "message": "Unknown message type",
            })

    async def _handle_two_player_game(self, message: Dict[str, Any]) -> Dict[str, Any]:
        session_id = message.get("session_id", "")
        session, _, _ = self.validate_inputs(session_id)
        two_player_game = message.get("payload", {})
        two_player_game_payload = TwoPlayerGamePayload(**two_player_game)
        system_prompt = prompts.get_two_player_game_system_prompt(two_player_game_payload)
        session.system_instructions = system_prompt
        await self.create_response_and_execute(
            {
                "message": "Start the game with a small, crisp announcement speech from the teacher. Then, emit the CLASSMATE_SPEECH command with the first speech from the classmate.",
                "instructions": session.system_instructions,
                "previous_response_id": session.previous_response_id
            },
            session
        )

    async def _handle_finish_two_player_game(self, message: Dict[str, Any]) -> Dict[str, Any]:
        session_id = message.get("session_id", "")
        session, _, _ = self.validate_inputs(session_id)
        await self.create_response_and_execute(
            {
                "message": "The game timer has now ended. End the game with a small, crisp concluding speech from the teacher. Emit <FINISH_MODULE/> at the end.",
                "instructions": session.system_instructions,
                "previous_response_id": session.previous_response_id
            },
            session
        )
        session.system_instructions = None

    async def start_phase(self, session: Session, course: Course, characters: List[Character]):
        phase_id = session.progress.phase_id if session.progress.phase_id is not None else 0
        phase = course.topics[session.progress.topic_id].modules[session.progress.module_id].phases[phase_id]
        session.progress.phase_id = phase_id
        if not session.system_instructions:
            # This does not mean that the session is not started. Dashboard building clears up the system instructions
            user = self.db.get_user(session.user_id)
            session.system_instructions = prompts.get_learning_interface_system_prompt(course.description, user, characters[0], characters[1])
        if session.status == SessionStatus.NOT_STARTED:
            session.status = SessionStatus.ACTIVE
            session.previous_response_id = None
            session.checkpoint_response_id = None
        else:
            session.previous_response_id = session.checkpoint_response_id
        self.log_event(session, "start_phase", {"progress": session.progress.model_dump()})
        content_string = "".join([cmd.to_string() for cmd in phase.content]) if phase.content else None
        phase_update_prompt = prompts.phase_update_prompt(content_string, phase.instruction)
        if phase.type == PhaseType.CONTENT:
            await self.execute_commands(phase.content, session)  
        await self.create_response_and_execute(
            {
                "message": phase_update_prompt,
                "instructions": session.system_instructions,
                "previous_response_id": session.previous_response_id
            },
            session
        )
    
    async def finish_module(self, session: Session, course: Course):
        session.status = SessionStatus.COMPLETED
        self.log_event(session, "finish_module", {})
        self.db.update_session(session.id, session.model_dump())
        # Can add some personalised feedback and messages here.
        await self.websocket.send_json({
            "type": "finish_module",
            "message": "Module finished",
        })
        dashboard_builder = DashboardBuilder(session.user_id)
        # Build dashboard upon session completion
        await dashboard_builder.build_dashboard()

    async def create_response_and_execute(self, create_response_args: dict, session):
        """
        openai text delta:
        {
            "type": "response.output_text.delta",
            "item_id": "msg_123",
            "output_index": 0,
            "content_index": 0,
            "delta": "In",
            "sequence_number": 1
        }
        """
        # response = await create_response(message=phase_update_prompt, instructions=session.system_instructions, previous_response_id=session.previous_response_id)
        create_response_args["stream"] = True
        response_stream = await create_response(**create_response_args)
        response_id = None
        command_parser = CommandParser()
        async for response in response_stream:
            if response.type == "response.created":
                response_id = response.response.id
            elif response.type == "response.output_text.delta":
                command_parser.add(response.delta)
                commands = command_parser.parse()
                await self.execute_commands(commands, session)
            elif response.type == "response.completed":
                print("Response completed")
        session.previous_response_id = response_id
        self.db.update_session_in_memory(session.id, session.model_dump())

    """
    For both types of speech commands, text and audio can be sent separately. The UI handles what to do based on the data available.
    """
    async def execute_commands(self, commands: List[Command], session: Session):
        for command in commands:
            try:
                if command.command_type in [CommandType.TEACHER_SPEECH, CommandType.CLASSMATE_SPEECH]:
                    # Handle commands that need streaming
                    await self.websocket.send_json({
                        "type": "command",
                        "command": command.model_dump()
                    })
                    self.log_event(session, "execute_command", {"command": command.model_dump()})
                    voice_id = session.teacher.voice_id if command.command_type == CommandType.TEACHER_SPEECH else session.classmate.voice_id
                    audio_stream = await create_speech_stream(command.payload.text, voice_id)
                    command.payload.text = None
                    
                    # Buffer audio chunks to reduce WebSocket message frequency
                    audio_buffer = b""
                    chunk_size_threshold = 16384  # Send chunks when buffer reaches this size
                    
                    async for chunk in audio_stream:
                        if isinstance(chunk, bytes):
                            audio_buffer += chunk
                            
                            # Send when buffer is large enough or this is the last chunk
                            if len(audio_buffer) >= chunk_size_threshold:
                                command.payload.audio_bytes = base64.b64encode(audio_buffer).decode('utf-8')
                                await self.websocket.send_json({
                                    "type": "command",
                                    "command": command.model_dump()
                                })
                                audio_buffer = b""  # Reset buffer
                    
                    # Send any remaining audio data
                    if audio_buffer:
                        command.payload.audio_bytes = base64.b64encode(audio_buffer).decode('utf-8')
                        await self.websocket.send_json({
                            "type": "command",
                            "command": command.model_dump()
                        })
                    
                    # Send a final message to indicate audio stream is complete
                    command.payload.audio_bytes = None
                    command.payload.stream_complete = True
                    await self.websocket.send_json({
                        "type": "command",
                        "command": command.model_dump()
                    })
                else:
                    # Handle commands that are flushed out at once
                    if command.command_type == CommandType.GAME:
                        game = self.db.get_game(command.payload.game_id)
                        command.payload.code = game.code
                    await self.websocket.send_json({
                        "type": "command",
                        "command": command.model_dump()
                    })
                self.log_event(session, "execute_command", {"command": command.model_dump()})
            except Exception as e:
                logger.error(f"Error executing command {command.command_type}: {str(e)}")
                await self.handle_error(None, f"Error executing command: {str(e)}")