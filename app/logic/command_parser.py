import json
from app.models.course import AckPayload, BinaryChoiceQuestionPayload, ClassmatePointPayload, ClassmateSpeechPayload, Command, CommandType, GamePayload, MultipleChoiceQuestionPayload, StudentPointPayload, TeacherSpeechPayload, WaitForStudentPayload, WhiteboardPayload


class CommandParser:
    def __init__(self):
        self.buffered_content = ""
        self.open_command = None
        self.open_command_content = None
        self.start_to_end_tags = {
            "<GAME>": "</GAME>",
            "<MCQ_QUESTION>": "</MCQ_QUESTION>",
            "<TEACHER_SPEECH>": "</TEACHER_SPEECH>",
            "<CLASSMATE_SPEECH>": "</CLASSMATE_SPEECH>",
            "<WHITEBOARD>": "</WHITEBOARD>",
            "<BINARY_CHOICE_QUESTION>": "</BINARY_CHOICE_QUESTION>",
            "<STUDENT_POINT>": "</STUDENT_POINT>",
            "<CLASSMATE_POINT>": "</CLASSMATE_POINT>",
        }
        self.standalone_tags = ["<FINISH_MODULE/>", "<ACKNOWLEDGE/>", "<WAIT_FOR_STUDENT/>"]
        self.valid_start_tags = ["<GAME>", "<MCQ_QUESTION>", "<TEACHER_SPEECH>", "<CLASSMATE_SPEECH>", "<WHITEBOARD>", "<BINARY_CHOICE_QUESTION>", "<STUDENT_POINT>", "<CLASSMATE_POINT>"]
    
    def add(self, text: str):
        self.buffered_content += text

    """
    How parsing works:
    First, check if any open command is there, as this needs to be closed first (no new command can be started if an existing command is already open)
        Find first instance of a closing tag for the open command.
        If no closing command is found, check if the text could contain a closing tag, but maybe not fully received yet (check for bracket character <)
        If no bracket is found, command is still open. Continue.
        If bracket is found, check if part after it could be a prefix of the expected end tag.
        If it is a prefix, command could be closing. Wait for next text (return current list of commands)
        If it is not a prefix, it is part of the open command's content. Add it.
    Now, check for new start commands (including standalone tags). This is a sanity check.
        If start tag is found and a command is still open (with no closing possibily in the text), then raise a parsing error.
    Check for start tags (excluding standalone tags)
        If found, parse the remaining (so that it goes over the open command flow again.)
    Check for standalong tags
        If found, parse the remaining to possibly find other commands
    """
    def parse(self):
        commands = []
        if self.open_command:
            expected_end_tag = self.start_to_end_tags[self.open_command]
            if expected_end_tag in self.buffered_content:
                end_tag_index = self.buffered_content.find(expected_end_tag)
                self.open_command_content += self.buffered_content[:end_tag_index]
                self.buffered_content = self.buffered_content[end_tag_index + len(expected_end_tag):]
                commands += self.handle_open_command(close=True)
            else:
                bracket_index = self.buffered_content.find("<")
                if bracket_index == -1:
                    self.open_command_content += self.buffered_content
                    commands += self.handle_open_command(close=False)
                    self.buffered_content = ""
                else:
                    # Parse out the part before <
                    self.open_command_content += self.buffered_content[:bracket_index]
                    self.buffered_content = self.buffered_content[bracket_index:]
                    # Check if the part after < is a prefix of the expected end tag
                    is_end_tag_prefix = expected_end_tag.startswith(self.buffered_content)
                    if is_end_tag_prefix:
                        return commands
                    else:
                        self.open_command_content += self.buffered_content
                        self.buffered_content = ""
                        commands += self.handle_open_command(close=False)
        for start_tag in self.valid_start_tags + self.standalone_tags:
            if start_tag in self.buffered_content and self.open_command:
                raise Exception("Start command found without an end tag for open command")
        has_start_tag = False
        for start_tag in self.valid_start_tags:
            if self.buffered_content.startswith(start_tag):
                has_start_tag = True
                self.open_command = start_tag
                self.open_command_content = ""
                self.buffered_content = self.buffered_content[len(start_tag):]
        # Start tag found, handle it
        if has_start_tag:
            commands += self.parse()
        has_standalone_tag = False
        for standalone_tag in self.standalone_tags:
            if self.buffered_content.startswith(standalone_tag):
                has_standalone_tag = True
                commands += self.handle_standalone_tags(standalone_tag)
                self.buffered_content = self.buffered_content[len(standalone_tag):]
                break
        if has_standalone_tag:
            commands += self.parse()
        return commands

    def handle_standalone_tags(self, tag):
        commands = []
        if tag == "<FINISH_MODULE/>":
            commands.append(Command(command_type=CommandType.FINISH_MODULE, payload=AckPayload()))
        elif tag == "<ACKNOWLEDGE/>":
            commands.append(Command(command_type=CommandType.ACKNOWLEDGE, payload=AckPayload()))
        elif tag == "<WAIT_FOR_STUDENT/>":
            commands.append(Command(command_type=CommandType.WAIT_FOR_STUDENT, payload=WaitForStudentPayload()))
        return commands

    def handle_open_command(self, close=False):
        def extract_speech_content(content):
            if close:
                return content
            # If not closed, send command with content until last punctuation mark
            punctuation_marks = ['.', '!', '?', ':']
            last_punctuation_index = -1
            for i in range(len(content) - 1, -1, -1):
                if content[i] in punctuation_marks:
                    last_punctuation_index = i
                    break
            return content[:last_punctuation_index + 1], content[last_punctuation_index + 1:]

        commands = []
        # Handle all command types here
        if self.open_command == "<GAME>":
            if not close:
                return commands
            game_id = self.open_command_content
            game_payload = GamePayload(game_id=game_id, code="")  # code will be filled in execute_commands
            commands.append(Command(command_type=CommandType.GAME, payload=game_payload))
        elif self.open_command == "<MCQ_QUESTION>":
            if not close:
                return commands
            mcq_question_json = json.loads(self.open_command_content)
            mcq_question = MultipleChoiceQuestionPayload(**mcq_question_json)
            commands.append(Command(command_type=CommandType.MCQ_QUESTION, payload=mcq_question))
        elif self.open_command == "<TEACHER_SPEECH>":
            if not self.open_command_content:
                return commands
            speech_content, remaining_content = extract_speech_content(self.open_command_content)
            if not speech_content:
                return commands
            self.open_command_content = remaining_content
            teacher_speech_payload = TeacherSpeechPayload(text=speech_content)
            commands.append(Command(command_type=CommandType.TEACHER_SPEECH, payload=teacher_speech_payload))
        elif self.open_command == "<CLASSMATE_SPEECH>":
            if not self.open_command_content:
                return commands
            speech_content, remaining_content = extract_speech_content(self.open_command_content)
            if not speech_content:
                return commands
            self.open_command_content = remaining_content
            classmate_speech_payload = ClassmateSpeechPayload(text=speech_content)
            commands.append(Command(command_type=CommandType.CLASSMATE_SPEECH, payload=classmate_speech_payload))
        elif self.open_command == "<WHITEBOARD>":
            if not close:
                return commands
            whiteboard_payload = WhiteboardPayload(html=self.open_command_content)
            commands.append(Command(command_type=CommandType.WHITEBOARD, payload=whiteboard_payload))
        elif self.open_command == "<BINARY_CHOICE_QUESTION>":
            if not close:
                return commands
            binary_choice_question_json = json.loads(self.open_command_content)
            binary_choice_question = BinaryChoiceQuestionPayload(**binary_choice_question_json)
            commands.append(Command(command_type=CommandType.BINARY_CHOICE_QUESTION, payload=binary_choice_question))
        elif self.open_command == "<STUDENT_POINT>":
            if not close:
                return commands
            student_point_payload = StudentPointPayload(point=self.open_command_content)
            commands.append(Command(command_type=CommandType.STUDENT_POINT, payload=student_point_payload))
        elif self.open_command == "<CLASSMATE_POINT>":
            if not close:
                return commands
            classmate_point_payload = ClassmatePointPayload(point=self.open_command_content)
            commands.append(Command(command_type=CommandType.CLASSMATE_POINT, payload=classmate_point_payload))
        # Close command
        if close:
            self.open_command = None
            self.open_command_content = ""
        return commands
