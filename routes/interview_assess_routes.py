from fastapi import APIRouter, Body
from controllers.interview_assess_controller import assess_candidate_interview,generate_next_question, get_interview_assessment, get_assessment_summary

router = APIRouter(prefix="/api/interview", tags=["Assessment"])

router.post("/assess-candidate")(assess_candidate_interview)
router.post("/next-question")(generate_next_question)
router.get("/assessment-summary/{application_id}")(get_assessment_summary)
router.get("/assessment/{application_id}")(get_interview_assessment)

