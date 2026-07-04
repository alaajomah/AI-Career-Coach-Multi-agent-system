from typing import Literal
from pydantic import BaseModel


class RouterDecision(BaseModel):
    agent: Literal["career", "resume", "interview"]