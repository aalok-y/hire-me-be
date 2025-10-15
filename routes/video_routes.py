from controllers.video_controller import upload_video
from fastapi import APIRouter


router = APIRouter(prefix="/api/video", tags=["Video"])


router.post("/upload-video")(upload_video)