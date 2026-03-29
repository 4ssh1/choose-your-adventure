import uuid
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Cookie, Response, BackgroundTasks
from sqlalchemy.orm import Session

from db.database import get_db, SessionLocal
from models.story import Story, StoryNode
from models.job import StoryJob
from schemas.story import CompleteStoryNodeRes, CompleteStoryRes, StoryCreate
from schemas.job import StoryJobRes

router = APIRouter(
    prefix= "/jobs",
    tags= ["jobs"]
)