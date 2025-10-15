from fastapi import APIRouter
from controllers.resume_controller import upload_resume,get_resume, upload_jd, get_jd
from controllers.resume_assessment_controller import assess_candidate, get_assessment


resume_router = APIRouter(prefix="/api/resume", tags=["Resume"])
job_router = APIRouter(prefix="/api/job", tags=["Job"])

resume_router.get("/{resume_id}")(get_resume)
resume_router.post("/upload-resume")(upload_resume)
resume_router.get("/assessment/{assessment_id}")(get_assessment)
resume_router.post("/assess-candidate")(assess_candidate)


job_router.get("/{job_id}")(get_jd)
job_router.post("/upload-jd")(upload_jd)
