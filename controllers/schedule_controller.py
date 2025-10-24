from fastapi import APIRouter, Body, HTTPException, Path, Query
from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId
from fastapi.concurrency import run_in_threadpool
from datetime import datetime
from config import interviews_collection
from dateutil.parser import parse




class InterviewScheduleRequest(BaseModel):
    resume_id: str = Field(..., description="MongoDB ObjectId as string")
    job_id: str = Field(..., description="MongoDB ObjectId as string")
    scheduled_time: str = Field(..., description="ISO8601 datetime string (UTC)")
    difficulty: str = Field(..., description="Difficulty level, e.g., 'easy', 'moderate', 'hard'")
    custom_instructions: Optional[str] = Field(None, description="Any extra instructions for the interview or interviewer")
    user_id: str

async def schedule_interview(request: InterviewScheduleRequest = Body(...)):
    # Validate ObjectIds
    if not ObjectId.is_valid(request.resume_id):
        raise HTTPException(status_code=400, detail="Invalid resume_id")
    if not ObjectId.is_valid(request.job_id):
        raise HTTPException(status_code=400, detail="Invalid job_id")
    if not ObjectId.is_valid(request.user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    try:
        # Optional: check datetime format
        try:
            scheduled_time = parse(request.scheduled_time)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid datetime format for scheduled_time. Use ISO8601 (e.g. 2025-10-14T12:00:00Z)")

        # Interview event to store
        interview_event = {
            "resume_id": request.resume_id,
            "job_id": request.job_id,
            "scheduled_time": request.scheduled_time,
            "difficulty": request.difficulty,
            "custom_instructions": request.custom_instructions,
            "user_id": request.user_id,  # Store user_id
            "created_at": datetime.utcnow().isoformat(),
            "status": "scheduled"
        }
        # Store in MongoDB
        result = await run_in_threadpool(
            interviews_collection.insert_one, interview_event
        )
        session_id = str(result.inserted_id)

        return {
            "message": "Interview scheduled",
            "interview_session_id": session_id,
            "scheduled_time": request.scheduled_time
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {str(e)}")


async def get_scheduled_interview(
    interview_session_id: str = Path(..., description="Interview session ObjectId")
):
    if not ObjectId.is_valid(interview_session_id):
        raise HTTPException(status_code=400, detail="Invalid interview_session_id")
    interview = await run_in_threadpool(
        interviews_collection.find_one, {"_id": ObjectId(interview_session_id)}
    )
    if not interview:
        raise HTTPException(status_code=404, detail="Interview session not found")
    # Convert _id to string for JSON serialization
    interview["_id"] = str(interview["_id"])
    return interview


async def get_all_scheduled_interviews(user_id: Optional[str] = Query(None, description="User ID to filter interviews")):
    filter_query = {}
    if user_id:
        filter_query["user_id"] = user_id  # Assuming interviews have a 'user_id' field
    cursor = interviews_collection.find(filter_query)
    interviews = await run_in_threadpool(list, cursor)
    # Convert ObjectIds to string for all documents
    for interview in interviews:
        interview["_id"] = str(interview["_id"])
    return interviews


