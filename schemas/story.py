from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel

class StoryOptions(BaseModel):
    node_id: Optional[int] = None
    text: str

class StoryNodeBase(BaseModel):
    content: str
    is_ending: bool = False
    is_winning: bool = False

class CompleteStoryNodeRes(StoryNodeBase):
    id: int
    options: List[StoryOptions] = []

    class Config:
        from_attributes = True

class StoryBase(BaseModel):
    title: str
    session_id: Optional[str] = None

    class Config:
        from_attributes = True

class StoryCreate(BaseModel):
    theme: str

class CompleteStoryRes(StoryBase):
    id: int
    created_at: datetime
    root_node: CompleteStoryNodeRes
    all_nodes: Dict[int, CompleteStoryNodeRes] 

    class Config:
        from_attributes = True