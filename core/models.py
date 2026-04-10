from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class LLMOption(BaseModel):
    text: str = Field(description="the text of the option shown to the user")
    nextNode: Dict[str, Any] = Field(description= "the next node content and its options")

class StoryLLM(BaseModel):
    content: str = Field(description="The main content of the story node")
    isEnding: bool = Field(description="Whether the node is an ending node")
    isWinningEnding: bool = Field(description="Whether the node is a winning ending node")
    options: Optional[List[LLMOption]] = Field(description="The options for this node", default=None)

class LLMRes(BaseModel):
    title: str = Field(description="The title of the story")
    rootNode: StoryLLM = Field(description= "The root node of the story")