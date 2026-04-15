import os
import json
import httpx
from sqlalchemy.orm import Session
from core.prompts import STORY_PROMPT
from core.models import LLMRes, StoryLLM
from models.story import Story, StoryNode
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
MODEL = "llama-3.3-70b-versatile"
BASE_URL = "https://api.groq.com/openai/v1/chat/completions"


class StoryGenerator:

    @classmethod
    def _call_llm(cls, system_prompt: str, user_message: str) -> str:
        response = httpx.post(
            BASE_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.9,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    @classmethod
    def generate_story(cls, db: Session, session_id: str, theme: str = "fantasy") -> Story:
        schema = LLMRes.model_json_schema()

        system_prompt = (
            f"{STORY_PROMPT}\n\n"
            "Respond ONLY with a valid JSON object matching this schema "
            "(no markdown fences, no extra text):\n"
            f"{json.dumps(schema, indent=2)}"
        )

        raw_text = cls._call_llm(system_prompt, f"Create the story with this theme: {theme}")

        story_structure = LLMRes.model_validate_json(raw_text)

        story_db = Story(title=story_structure.title, session_id=session_id)
        db.add(story_db)
        db.flush()
        db.refresh(story_db)

        if story_db.id is None:
            raise ValueError("Story DB ID was not set after flush")

        root_node_data = story_structure.rootNode
        if isinstance(root_node_data, dict):
            root_node_data = StoryLLM.model_validate(root_node_data)

        cls._process_story_node(db, story_db.id, root_node_data, is_root=True)

        db.commit()
        return story_db

    @classmethod
    def _process_story_node(
        cls,
        db: Session,
        story_id: int,
        node_data: StoryLLM,
        is_root: bool = False,
    ) -> StoryNode:
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

        if not node.is_ending and node_data.options:
            options_list = []
            for option_data in node_data.options:
                next_node = option_data.nextNode
                if isinstance(next_node, dict):
                    next_node = StoryLLM.model_validate(next_node)

                child_node = cls._process_story_node(db, story_id, next_node, False)
                options_list.append({"text": option_data.text, "node_id": child_node.id})

            node.options = options_list
            db.flush()

        return node