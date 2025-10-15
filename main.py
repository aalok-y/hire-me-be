
from config import app
from routes.resume_routes import resume_router
from routes.job_routes import job_router
from routes.interview_assess_routes import router as interview_router
from routes.speech_routes import router as speech_router
from routes.schedule_routes import router as schedule_router
from auth.routes import router as auth_router
from routes.video_routes import router as video_router


app.include_router(auth_router)
app.include_router(resume_router)
app.include_router(job_router)
app.include_router(interview_router)
app.include_router(speech_router)
app.include_router(schedule_router)
app.include_router(video_router)



@app.get("/")
async def root():
    return {"message": "AI Interview Platform API is running"}


# Run using:
# uvicorn main:app --reload
