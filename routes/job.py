from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from models.job import StoryJob
from schemas.job import StoryJobRes

router = APIRouter(
    prefix= "/jobs",
    tags= ["jobs"]
)

@router.get("/{jobId}", response_model=StoryJobRes)
def get_job_status(jobId: str, db: Session = Depends(get_db)):
    job = db.query(StoryJob).filter(StoryJob.job_id == jobId).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job