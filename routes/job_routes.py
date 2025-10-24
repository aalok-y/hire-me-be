from fastapi import APIRouter
from controllers.job_controller import  upload_jd, get_jd, apply_job, get_applicants_for_job
from typing import List


job_router = APIRouter(prefix="/api/job", tags=["Job"])

job_router.get("/{job_id}")(get_jd)
job_router.post("/upload-jd")(upload_jd)
job_router.post("/apply")(apply_job)
job_router.get("/{job_id}/applicants", response_model=List[dict])(get_applicants_for_job)
job_router.get("/{user_id}/jobs", response_model=List[str])
