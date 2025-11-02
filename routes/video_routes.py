from controllers.video_controller import upload_video, save_merged_video, get_interview_video, list_interview_videos, delete_interview_video
from fastapi import APIRouter


router = APIRouter(prefix="/api/video", tags=["Video"])


router.post("/upload-video")(upload_video)
router.post("/save-merged-video")(save_merged_video)
router.get("/download-merged-video/{application_id}")(get_interview_video)
router.get("/{application_id}/{user_id}")(get_interview_video)
router.get("/videos/list/{user_id}")(list_interview_videos)
router.delete("/{application_id}/{user_id}")(delete_interview_video)

