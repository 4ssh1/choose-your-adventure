from sqlalchemy.orm import Session
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from core.config import Settings
from core.prompts import STORY_PROMPT
from core.models import LLMRes, StoryLLM
from models.story import Story, StoryNode


from typing import cast


class StoryGenerator:
    @classmethod
    def _get_llm(cls):
        return ChatOpenAI(model='gpt-4-turbo')
    
    @classmethod
    def generate_story(cls, db: Session, session_id: str, theme:str = "fantasy") -> Story:
        llm = cls._get_llm()
        story_parser = PydanticOutputParser(pydantic_object=LLMRes)
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                STORY_PROMPT
            ),
            (
                "human",
                f"Create the story with this theme: {theme}"
            )
        ]).partial(format_instruction= story_parser.get_format_instructions())

        raw_response = llm.invoke(prompt.invoke({}))

        if not isinstance(raw_response.content, str):
            raise ValueError("LLM response content is not a string")

        response_text = raw_response.content

        story_structure: LLMRes = story_parser.parse(response_text)

        story_db = Story(title=story_structure.title, session_id=session_id)
        db.add(story_db)
        db.flush()
        db.refresh(story_db)

        root_node_data = story_structure.rootNode

        if isinstance(root_node_data, dict):
            root_node_data = StoryLLM.model_validate(root_node_data)

        if story_db.id is None:
            raise ValueError("Story DB ID is not set")

        cls._process_story_node(db, story_db.id, root_node_data, is_root= True)

        db.commit()
        return story_db
    
    @classmethod
    def _process_story_node(cls, db:Session, story_id: int, node_data: StoryLLM, is_root:bool = False):
        node = StoryNode(
            story_id=story_id,
            content=node_data.content,
            is_root=is_root,
            is_ending=node_data.isEnding,
            is_winning=node_data.isWinningEnding,
            options=[]
        )

        db.add(node)
        db.flush()

        if not node.is_ending and (hasattr(node_data, "options") and node_data.options):
            options_list = []
            for option_data in node_data.options:
                next_node = option_data.nextNode

                if isinstance(next_node, dict):
                    next_node = StoryLLM.model_validate(next_node)

                child_node = cls._process_story_node(db, story_id, next_node, False)

                options_list.append({
                    "text": option_data.text,
                    "node_id": child_node.id
                })

                node.options = options_list

        db.flush()
        return node
