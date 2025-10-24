from fastapi import FastAPI, File, UploadFile, HTTPException, Body, Form
from bson import ObjectId
from config import app
from services.parsers import extract_text_from_pdf,parse_resume_with_gemini, extract_json_from_gemini_response
from utils.pymango_wrappers import async_insert_one,async_find_one 
from config import resumes_collection
from services.parsers import parse_jd_with_gemini
from config import resumes_collection, jds_collection, applications_collection
from utils.pymango_wrappers import convert_objectids
import time




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



async def apply_job(user_id: str, resume_id: str, job_id: str):
    # Validate Object IDs
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    if not ObjectId.is_valid(resume_id):
        raise HTTPException(status_code=400, detail="Invalid resume_id")
    if not ObjectId.is_valid(job_id):
        raise HTTPException(status_code=400, detail="Invalid job_id")

    user_obj_id = ObjectId(user_id)
    resume_obj_id = ObjectId(resume_id)
    job_obj_id = ObjectId(job_id)

    # Define application data
    application_data = {
        "user_id": user_obj_id,
        "resume_id": resume_obj_id,
        "job_id": job_obj_id,
        "status": "rejected",  
        "application_date": time.time()  
    }

    # Store application in the collection
    result = await applications_collection.insert_one(application_data)

    return {"application_id": str(result.inserted_id), "status": "Application submitted successfully"}


async def get_applicants_for_job(job_id: str):
    # Validate job_id
    if not ObjectId.is_valid(job_id):
        raise HTTPException(status_code=400, detail="Invalid job_id")

    job_obj_id = ObjectId(job_id)

    # Query applications for this job
    cursor = applications_collection.find({"job_id": job_obj_id})

    applicants = []
    async for doc in cursor:
        applicants.append({
            "user_id": str(doc.get("user_id")),
            "resume_id": str(doc.get("resume_id")),
            "status": doc.get("status")
        })

    return applicants





async def get_jobs_created_by_user(user_id: str):
    # Validate user_id
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    user_obj_id = ObjectId(user_id)

    # Query jobs created by this user
    cursor = jds_collection.find({"creator_user_id": user_obj_id}, {"_id": 1})

    job_ids = []
    async for doc in cursor:
        job_ids.append(str(doc["_id"]))

    return job_ids
