from pydantic import BaseModel


class Game(BaseModel):
    id: str
    name: str
    description: str
    code: str
