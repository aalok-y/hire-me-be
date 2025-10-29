import os
from fastapi import APIRouter, UploadFile, File, HTTPException


VIDEO_SAVE_DIR = "/home/machine/Downloads/temp/interview-video"


async def upload_video(file: UploadFile = File(...)):
    # Validate file type (optional, check typical video mime types or extensions)
    if not file.filename.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
        raise HTTPException(status_code=400, detail="Unsupported video format")

    # Create directory if it does not exist
    os.makedirs(VIDEO_SAVE_DIR, exist_ok=True)

    file_location = os.path.join(VIDEO_SAVE_DIR, file.filename)

    try:
        # Read file content asynchronously
        content = await file.read()
        # Write the file to disk
        with open(file_location, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save video: {str(e)}")

    return {"message": "Video uploaded successfully", "filename": file.filename}
