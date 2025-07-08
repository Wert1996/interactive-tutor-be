
import json
import os
from typing import Any, Dict, Union

from app.models.course import Course
from app.models.session import Session
from app.models.user import User


def load_json_data(file_path: str) -> Dict[str, Any]:
    """Load data from a JSON file."""
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

def save_json_data(file_path: str, data: Dict[str, Any]) -> None:
    """Save data to a JSON file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=2)

class Db:
    _instance = None
    
    @staticmethod
    def get_instance():
        if not Db._instance:
            Db._instance = Db()
        return Db._instance
    
    def __init__(self):
        self.users = load_json_data("app/data/users.json")
        self.courses = load_json_data("app/data/courses.json")
        self.sessions = load_json_data("app/data/sessions.json")

    def get_session(self, session_id: str):
        session_json = self.sessions.get(session_id, None)
        if not session_json:
            return None
        return Session(**session_json)
    
    def get_user(self, user_id: str):
        user_json = self.users.get(user_id, None)
        if not user_json:
            return None
        return User(**user_json)
    
    def create_user(self, user_id: str, user_data: Dict[str, Any]):
        self.users[user_id] = user_data
        save_json_data("app/data/users.json", self.users)

    def update_session(self, session_id: str, session_data: Dict[str, Any]):
        self.sessions[session_id] = session_data
        save_json_data("app/data/sessions.json", self.sessions)
    
    def update_session_in_memory(self, session_id: str, session_data: Union[Dict[str, Any], Session]):
        if isinstance(session_data, Session):
            self.sessions[session_id] = session_data.model_dump()
        else:
            self.sessions[session_id] = session_data

    def update_user(self, user_id: str, user_data: Dict[str, Any]):
        self.users[user_id] = user_data
        save_json_data("app/data/users.json", self.users)
    
    def update_course(self, course_id: str, course_data: Dict[str, Any]):
        self.courses[course_id] = course_data
        save_json_data("app/data/courses.json", self.courses)

    def get_course(self, course_id: str):
        course_json = self.courses.get(course_id, None)
        if not course_json:
            return None
        return Course(**course_json)