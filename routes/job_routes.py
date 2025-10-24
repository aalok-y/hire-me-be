from fastapi import APIRouter, status
from controllers.job_controller import upload_jd, get_jd, apply_job, get_applicants_for_job, delete_job, jobs_created_by_user, get_all_jobs, application_status, my_applications
from typing import List

job_router = APIRouter(prefix="/api/job", tags=["Job"])

job_router.post("/upload-jd")(upload_jd)
job_router.post("/apply")(apply_job)
job_router.get("/all")(get_all_jobs)
job_router.get("/status")(application_status)
job_router.get("/my-applications", response_model=List[dict])(my_applications)

job_router.get("/{user_id}/jobs", response_model=List[str])(jobs_created_by_user)
job_router.get("/{job_id}/applicants", response_model=List[dict])(get_applicants_for_job)

job_router.get("/{job_id}")(get_jd)
job_router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)(delete_job)
