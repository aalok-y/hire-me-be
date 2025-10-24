from fastapi import APIRouter
from controllers.schedule_controller import schedule_interview, get_scheduled_interview, get_all_scheduled_interviews


router = APIRouter(prefix="/api/schedule", tags=["Schedule"])

router.post("/schedule-interview")(schedule_interview)
router.get("/interview/{interview_session_id}")(get_scheduled_interview)
router.get("/interviews")(get_all_scheduled_interviews)