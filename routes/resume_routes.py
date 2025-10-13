from fastapi import APIRouter, Body
from controllers.resume_controller import upload_resume,get_resume, upload_jd

router = APIRouter(prefix="/api", tags=["Resume"])

router.get("/resume/{resume_id}")(get_resume)
router.post("/upload-resume")(upload_resume)
router.post("/upload-jd")(upload_jd)



