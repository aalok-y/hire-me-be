from fastapi import APIRouter, Body
from controllers.assessment_controller import assess_candidate, get_assessment

router = APIRouter(prefix="/api", tags=["Assessment"])

router.get("/assessment/{assessment_id}")(get_assessment)
router.post("/assess-candidate")(assess_candidate)

