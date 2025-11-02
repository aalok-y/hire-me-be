import os
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
import shutil
import os
from datetime import datetime
import logging


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



# Configure upload directory
UPLOAD_DIR = Path("/home/machine/Downloads/temp/merged-interview-video")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

async def save_merged_video(
    video: UploadFile = File(...),
    application_id: str = Form(...),
    user_id: str = Form(...)
):
    """
    Save the merged interview video (candidate + interviewer audio)
    
    Args:
        video: The merged video file
        application_id: Application ID for the interview
        user_id: User ID of the candidate
    
    Returns:
        dict: Success message with file path
    """
    try:
        # Create user-specific directory
        user_dir = UPLOAD_DIR / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"interview_{application_id}_{timestamp}.webm"
        file_path = user_dir / filename
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
        
        # Optionally: Store file path in database
        # await store_video_path_in_db(application_id, str(file_path))
        
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        
        return {
            "message": "Merged video saved successfully",
            "application_id": application_id,
            "file_path": str(file_path),
            "filename": filename,
            "size_mb": round(file_size_mb, 2)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error saving merged video: {str(e)}"
        )

async def get_interview_video(application_id: str, user_id: str):
    """
    Download the merged interview video
    
    Args:
        application_id: Application ID
        user_id: User ID
    
    Returns:
        FileResponse: The video file
    """
    from fastapi.responses import FileResponse
    
    user_dir = UPLOAD_DIR / user_id
    
    # Find the file matching the application_id
    matching_files = list(user_dir.glob(f"interview_{application_id}_*.webm"))
    
    if not matching_files:
        raise HTTPException(
            status_code=404,
            detail="Merged video not found"
        )
    
    # Return the most recent file if multiple exist
    file_path = max(matching_files, key=lambda p: p.stat().st_mtime)
    
    return FileResponse(
        path=str(file_path),
        media_type="video/webm",
        filename=file_path.name
    )





# Configure logging
logger = logging.getLogger(__name__)



async def get_interview_video(
    application_id: str,
    user_id: str,
    request: Request
):
    """
    Download/stream the merged interview video
    
    Supports:
    - Multiple video files (returns the latest one)
    - Browser playback with video tag
    - Range requests for seeking in video
    - Proper error handling
    
    Args:
        application_id: Application ID
        user_id: User ID
    
    Returns:
        FileResponse: The video file with proper headers for browser playback
    
    Raises:
        HTTPException 404: If no video found
        HTTPException 403: If user directory doesn't exist or is inaccessible
    """
    try:
        # Validate inputs
        if not application_id or not user_id:
            raise HTTPException(
                status_code=400,
                detail="application_id and user_id are required"
            )
        
        logger.info(f"Retrieving video for user={user_id}, app_id={application_id}")
        
        # Build user directory path
        user_dir = UPLOAD_DIR / user_id
        
        # Check if user directory exists
        if not user_dir.exists():
            logger.warning(f"User directory not found: {user_dir}")
            raise HTTPException(
                status_code=404,
                detail=f"No interviews found for user {user_id}"
            )
        
        # Find all matching video files
        matching_files = list(user_dir.glob(f"interview_{application_id}_*.webm"))
        
        if not matching_files:
            logger.warning(f"No video files found for app_id={application_id} in {user_dir}")
            raise HTTPException(
                status_code=404,
                detail=f"No interview video found for application {application_id}"
            )
        
        # Get the most recent file if multiple exist
        file_path = max(matching_files, key=lambda p: p.stat().st_mtime)
        
        logger.info(f"Found {len(matching_files)} video file(s), returning latest: {file_path.name}")
        
        # Verify file still exists and is readable
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Video file no longer exists"
            )
        
        if not os.access(file_path, os.R_OK):
            logger.error(f"Permission denied reading file: {file_path}")
            raise HTTPException(
                status_code=403,
                detail="Permission denied accessing video file"
            )
        
        # Get file stats
        file_size = file_path.stat().st_size
        last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
        
        logger.info(
            f"Serving video: {file_path.name}, "
            f"size={file_size / (1024*1024):.2f}MB, "
            f"modified={last_modified}"
        )
        
        # Check for range request (seeking in video)
        range_header = request.headers.get("range")
        
        if range_header:
            return handle_range_request(file_path, range_header, file_size)
        
        # Return file for browser playback
        return FileResponse(
            path=str(file_path),
            media_type="video/webm",
            filename=file_path.name,
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=3600",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving interview video: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving interview video: {str(e)}"
        )


def handle_range_request(file_path: Path, range_header: str, file_size: int) -> StreamingResponse:
    """
    Handle HTTP range requests for video seeking
    
    Args:
        file_path: Path to the video file
        range_header: Range header value (e.g., "bytes=1024000-2048000")
        file_size: Total file size in bytes
    
    Returns:
        StreamingResponse: Partial content response
    """
    try:
        # Parse range header
        range_value = range_header.strip().replace("bytes=", "")
        
        if "-" not in range_value:
            raise ValueError("Invalid range format")
        
        start_str, end_str = range_value.split("-", 1)
        
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
        
        # Validate range
        if start >= file_size or end >= file_size or start > end:
            raise ValueError("Range out of bounds")
        
        # Calculate content length
        content_length = end - start + 1
        
        logger.info(f"Serving range: bytes {start}-{end}/{file_size} ({content_length} bytes)")
        
        # Stream the requested range
        def range_generator():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                chunk_size = 1024 * 1024  # 1MB chunks
                
                while remaining > 0:
                    read_size = min(chunk_size, remaining)
                    chunk = f.read(read_size)
                    if not chunk:
                        break
                    yield chunk
                    remaining -= len(chunk)
        
        return StreamingResponse(
            range_generator(),
            status_code=206,  # Partial Content
            media_type="video/webm",
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(content_length),
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=3600",
            }
        )
        
    except (ValueError, IndexError) as e:
        logger.warning(f"Invalid range request: {range_header}, error: {str(e)}")
        # Return full file if range is invalid
        return FileResponse(
            path=str(file_path),
            media_type="video/webm",
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=3600",
            }
        )


async def list_interview_videos(user_id: str):
    """
    List all interview videos for a user
    
    Args:
        user_id: User ID
    
    Returns:
        dict: List of video files with metadata
    """
    try:
        if not user_id:
            raise HTTPException(
                status_code=400,
                detail="user_id is required"
            )
        
        user_dir = UPLOAD_DIR / user_id
        
        if not user_dir.exists():
            return {
                "user_id": user_id,
                "videos": [],
                "total_count": 0
            }
        
        # Get all video files
        video_files = sorted(user_dir.glob("interview_*.webm"), 
                           key=lambda p: p.stat().st_mtime, 
                           reverse=True)
        
        videos = []
        total_size = 0
        
        for video_file in video_files:
            stat = video_file.stat()
            size_mb = stat.st_size / (1024 * 1024)
            total_size += stat.st_size
            
            # Extract application_id from filename
            app_id = video_file.name.split("_")[1]  # interview_APP_ID_timestamp
            
            videos.append({
                "filename": video_file.name,
                "application_id": app_id,
                "size_mb": round(size_mb, 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "url": f"/api/interview/video/{app_id}/{user_id}"
            })
        
        return {
            "user_id": user_id,
            "videos": videos,
            "total_count": len(videos),
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
        
    except Exception as e:
        logger.error(f"Error listing videos: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error listing videos: {str(e)}"
        )


async def delete_interview_video(application_id: str, user_id: str):
    """
    Delete interview video(s) for an application
    
    Args:
        application_id: Application ID
        user_id: User ID
    
    Returns:
        dict: Deletion confirmation
    """
    try:
        if not application_id or not user_id:
            raise HTTPException(
                status_code=400,
                detail="application_id and user_id are required"
            )
        
        user_dir = UPLOAD_DIR / user_id
        
        if not user_dir.exists():
            raise HTTPException(
                status_code=404,
                detail="User directory not found"
            )
        
        # Find all matching videos
        matching_files = list(user_dir.glob(f"interview_{application_id}_*.webm"))
        
        if not matching_files:
            raise HTTPException(
                status_code=404,
                detail="No videos found to delete"
            )
        
        deleted_files = []
        
        # Delete all matching files
        for file_path in matching_files:
            try:
                file_path.unlink()
                deleted_files.append(file_path.name)
                logger.info(f"Deleted video: {file_path}")
            except Exception as e:
                logger.error(f"Error deleting file {file_path}: {str(e)}")
        
        return {
            "message": "Videos deleted successfully",
            "deleted_count": len(deleted_files),
            "deleted_files": deleted_files
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting interview video: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting interview video: {str(e)}"
        )
