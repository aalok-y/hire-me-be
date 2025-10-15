from fastapi import APIRouter, Body
from controllers.resume_controller import upload_resume,get_resume, upload_jd
from controllers.resume_assessment_controller import assess_candidate, get_assessment


router = APIRouter(prefix="/api/resume", tags=["Resume"])

router.get("/{resume_id}")(get_resume)
router.post("/upload-resume")(upload_resume)
router.post("/upload-jd")(upload_jd)
router.get("/assessment/{assessment_id}")(get_assessment)
router.post("/assess-candidate")(assess_candidate)


