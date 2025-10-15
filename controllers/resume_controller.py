from fastapi import FastAPI, File, UploadFile, HTTPException, Body, Form
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from bson import ObjectId
from config import app
from services.parsers import extract_text_from_pdf,parse_resume_with_gemini, extract_json_from_gemini_response
from utils.pymango_wrappers import async_insert_one,async_find_one 
from config import resumes_collection
from services.parsers import parse_jd_with_gemini
from config import resumes_collection, jds_collection
from utils.pymango_wrappers import convert_objectids



async def upload_resume(
    file: UploadFile = File(...),
    user_id: str = Form(...)
):
    # Validate user_id as ObjectId
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    try:
        pdf_bytes = await file.read()
        text = extract_text_from_pdf(pdf_bytes)
        if not text.strip():
            raise HTTPException(status_code=400, detail="Empty PDF text")

        parsed_resume = await parse_resume_with_gemini(text)
        resume_data = parsed_resume.model_dump()
        resume_data["original_filename"] = file.filename
        resume_data["raw_text"] = text
        resume_data["user_id"] = user_id  # Add user_id to saved doc

        result = await async_insert_one(resumes_collection, resume_data)
        return {
            "message": "Resume parsed and stored",
            "resume_id": str(result.inserted_id),
            "candidate_name": parsed_resume.resume.header.full_name,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

async def get_resume(resume_id: str):
    resume_id = ObjectId(resume_id.strip())
    if not ObjectId.is_valid(resume_id):
        raise HTTPException(status_code=400, detail="Invalid resume ID")
    resume = await async_find_one(resumes_collection, {"_id": ObjectId(resume_id)})
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    resume["_id"] = str(resume["_id"])
    return resume



async def get_jd(job_id: str):
    job_id = job_id.strip()
    if not ObjectId.is_valid(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")

    job_doc = await async_find_one(jds_collection, {"_id": ObjectId(job_id)})
    if not job_doc:
        raise HTTPException(status_code=404, detail="Job description not found")

    job_doc = convert_objectids(job_doc)  # recursively convert ObjectIds
    return job_doc



async def upload_jd(
    file: UploadFile = File(...),
    user_id: str = Form(...)
):
    # Validate user_id
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    try:
        # Read file bytes
        pdf_bytes = await file.read()

        # Extract raw text from the uploaded PDF
        jd_text = extract_text_from_pdf(pdf_bytes)
        if not jd_text.strip():
            raise HTTPException(status_code=400, detail="Empty PDF text extracted")

        # Parse the JD text into structured format using Gemini
        parsed_jd = await parse_jd_with_gemini(jd_text)
        jd_data = parsed_jd.model_dump()
        jd_data["original_filename"] = file.filename
        jd_data["raw_text"] = jd_text
        jd_data["user_id"] = ObjectId(user_id)

        # Insert structured JD into MongoDB
        result = await async_insert_one(jds_collection, jd_data)

        return {
            "message": "Job description parsed and stored",
            "jd_id": str(result.inserted_id),
            "job_title": parsed_jd.job_title,
            "user_id": user_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job description upload failed: {str(e)}")
