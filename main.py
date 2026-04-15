from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.rate_limit import InMemoryRateLimitMiddleware, RateLimitConfig
from routes import story, job
from db.database import create_tables

create_tables()
    
app = FastAPI(
    title= "Choose Your Own Adventure API",
    description= "An API for a choose your own adventure game to generate cool stories",
    version= "1.0.0",
    docs_url= "/docs",
    redoc_url= "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(
        InMemoryRateLimitMiddleware,
        config=RateLimitConfig(
            requests=settings.RATE_LIMIT_REQUESTS,
            window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
        ),
    )

app.include_router(story.router, prefix=settings.API_PREFIX)
app.include_router(job.router, prefix=settings.API_PREFIX)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)