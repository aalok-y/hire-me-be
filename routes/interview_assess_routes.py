from fastapi import APIRouter, Body
from controllers.interview_assess_controller import assess_candidate_interview,generate_next_question

router = APIRouter(prefix="/api/interview", tags=["Assessment"])

router.post("/assess-candidate")(assess_candidate_interview)
router.post("/next-question")(generate_next_question)
