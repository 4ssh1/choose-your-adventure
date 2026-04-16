import uuid
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Cookie, Response, BackgroundTasks
from sqlalchemy.orm import Session

from db.database import get_db, SessionLocal
from models.story import Story, StoryNode
from models.job import StoryJob
from schemas.story import CompleteStoryNodeRes, CompleteStoryRes, StoryCreate, StoryOptions
from schemas.job import StoryJobRes
from core.story_generator import StoryGenerator

router = APIRouter(
    prefix= "/stories",
    tags= ["stories"]
) 

def get_session_id(session_id: Optional[str] = Cookie(None)) -> str:
    if session_id is None:
        session_id = str(uuid.uuid4())
    return session_id


@router.post(path= "/", response_model=StoryJobRes)
def create_story(
    request: StoryCreate,
    background_tasks: BackgroundTasks,
    response: Response,
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db)
):
    response.set_cookie(key="session_id", value=session_id, httponly=True)

    job_id = str(uuid.uuid4())

    job = StoryJob(
        job_id= job_id,
        session_id=session_id,
        theme= request.theme,
        status= "pending"
    )

    db.add(job)
    db.commit()

    background_tasks.add_task(
        generate_story_task,
        job_id,
        request.theme,
        session_id
    )

    return job


def generate_story_task(job_id: str, theme: str, session_id: str) -> None:
    db = SessionLocal()

    try:
        job = db.query(StoryJob).filter(StoryJob.job_id == job_id).first()

        if not job:
            return

        try:
            job.status = "processing"
            db.commit()

            story = StoryGenerator.generate_story(db=db, session_id=session_id, theme=theme)

            job.story_id = story.id
            job.status = "completed"
            job.completed_at = datetime.now()
            db.commit()
        except Exception as e:
            job.status = "failed"
            job.completed_at = datetime.now()
            job.error = str(e)
            db.commit()

    finally:
        db.close()

@router.get("/{storyId}", response_model=CompleteStoryRes)
def get_complete_story(storyId: int, db: Session = Depends(get_db)):
    story = db.query(Story).filter(Story.id == storyId).first()
    if not story:
        raise HTTPException(404, detail="Story not found")

    return build_story_tree(db, story)
    

def build_story_tree(db: Session, story: Story) -> CompleteStoryRes:
    nodes = db.query(StoryNode).filter(StoryNode.story_id == story.id).all()

    if not nodes:
        raise HTTPException(404, detail="Story nodes not found")

    all_nodes: dict[int, CompleteStoryNodeRes] = {}
    root_node: Optional[CompleteStoryNodeRes] = None

    for node in nodes:
        options: list[StoryOptions] = []
        if isinstance(node.options, list):
            for option in node.options:
                if not isinstance(option, dict):
                    continue

                text = option.get("text")
                node_id = option.get("node_id")

                if isinstance(text, str):
                    options.append(
                        StoryOptions(
                            text=text,
                            node_id=node_id if isinstance(node_id, int) else None,
                        )
                    )

        node_res = CompleteStoryNodeRes(
            id=node.id,
            content=node.content,
            is_ending=node.is_ending,
            is_winning=node.is_winning,
            options=options,
        )
        all_nodes[node.id] = node_res

        if node.is_root:
            root_node = node_res

    if root_node is None:
        root_node = next(iter(all_nodes.values()))

    return CompleteStoryRes(
        id=story.id,
        title=story.title,
        session_id=story.session_id,
        created_at=story.created_at,
        root_node=root_node,
        all_nodes=all_nodes,
    )