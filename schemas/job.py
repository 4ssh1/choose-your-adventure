from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class StoryJobBase(BaseModel):
    theme:str

class StoryJobRes(BaseModel):
    job_id: str
    status: str
    story_id: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str]

    class Config:
        from_attributes = True

class StoryJobCreate(StoryJobBase):
    pass
