from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Query, BackgroundTasks
from bson import ObjectId
from config import app
from services.parsers import extract_text_from_pdf,parse_resume_with_gemini, extract_json_from_gemini_response
from utils.pymango_wrappers import async_insert_one,async_find_one 
from config import resumes_collection
from services.parsers import parse_jd_with_gemini
from config import resumes_collection, jds_collection, applications_collection
from utils.pymango_wrappers import convert_objectids
import time
from pymongo.errors import PyMongoError
from typing import List
from pydantic import BaseModel
import requests



async def get_jd(job_id: str):
    job_id = job_id.strip()
    if not ObjectId.is_valid(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")

    job_doc = await async_find_one(jds_collection, {"_id": ObjectId(job_id)})
    if not job_doc:
        raise HTTPException(status_code=404, detail="Job description not found")

    job_doc = convert_objectids(job_doc)  
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


class JobApplication(BaseModel):
    user_id: str
    resume_id: str
    job_id: str


def assess_candidate_background(application_id: str, resume_id: str, job_id: str):
    """Background task to assess candidate"""
    try:
        # Call the assessment endpoint
        response = requests.post(
            "http://localhost:8000/api/resume/assess-candidate",
            json={
                "resume_id": resume_id,
                "job_id": job_id
            }
        )
        
        if response.status_code == 200:
            assessment_data = response.json()
            # Update application status with assessment_id
            applications_collection.update_one(
                {"_id": ObjectId(application_id)},
                {
                    "$set": {
                        "assessment_id": assessment_data.get("assessment_id"),
                        "status": "resume_assessed"
                    }
                }
            )
        else:
            # Mark as failed assessment
            applications_collection.update_one(
                {"_id": ObjectId(application_id)},
                {"$set": {"status": "assessment_failed"}}
            )
    except Exception as e:
        print(f"Background assessment failed: {e}")
        applications_collection.update_one(
            {"_id": ObjectId(application_id)},
            {"$set": {"status": "assessment_failed"}}
        )


def apply_job(application: JobApplication, background_tasks: BackgroundTasks):
    # Validate Object IDs
    if not ObjectId.is_valid(application.user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    if not ObjectId.is_valid(application.resume_id):
        raise HTTPException(status_code=400, detail="Invalid resume_id")
    if not ObjectId.is_valid(application.job_id):
        raise HTTPException(status_code=400, detail="Invalid job_id")

    user_obj_id = ObjectId(application.user_id)
    resume_obj_id = ObjectId(application.resume_id)
    job_obj_id = ObjectId(application.job_id)

    # Define application data
    application_data = {
        "user_id": user_obj_id,
        "resume_id": resume_obj_id,
        "job_id": job_obj_id,
        "status": "pending",
        "application_date": time.time()
    }

    try:
        # Store application in the collection
        result = applications_collection.insert_one(application_data)
        application_id = str(result.inserted_id)
        
        # Add background task to assess candidate
        background_tasks.add_task(
            assess_candidate_background,
            application_id,
            application.resume_id,
            application.job_id
        )
        
        return {
            "application_id": application_id,
            "status": "Application submitted successfully. Assessment in progress."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to submit application")



def get_applicants_for_job(job_id: str):
    # Validate job_id
    if not ObjectId.is_valid(job_id):
        raise HTTPException(status_code=400, detail="Invalid job_id")

    job_obj_id = ObjectId(job_id)

    try:
        # Query applications for this job
        cursor = applications_collection.find({"job_id": job_obj_id})

        applicants = []
        for doc in cursor:
            applicants.append({
                "user_id": str(doc.get("user_id")),
                "resume_id": str(doc.get("resume_id")),
                "status": doc.get("status"),
                "application_id": str(doc.get("_id"))
            })
        
        return applicants
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch applicants")





def jobs_created_by_user(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    user_obj_id = ObjectId(user_id)

    job_ids = []
    try:
        cursor = jds_collection.find({"user_id": user_obj_id}, {"_id": 1})
        for doc in cursor:
            job_ids.append(str(doc["_id"]))
    except PyMongoError:
        raise HTTPException(status_code=500, detail="Database query error")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

    return job_ids


def delete_job(job_id: str):
    if not ObjectId.is_valid(job_id):
        raise HTTPException(status_code=400, detail="Invalid job_id")

    job_obj_id = ObjectId(job_id)

    delete_result = jds_collection.delete_one({"_id": job_obj_id})

    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")

    return None


def get_all_jobs():
    job_ids = []
    try:
        cursor = jds_collection.find({}, {"_id": 1})
        for doc in cursor:
            job_ids.append(str(doc["_id"]))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch jobs from database")
    return job_ids


def application_status(application_id: str = Query(...)):
    if not ObjectId.is_valid(application_id):
        raise HTTPException(status_code=400, detail="Invalid application_id")
    
    app_obj_id = ObjectId(application_id)
    
    try:
        application = applications_collection.find_one({"_id": app_obj_id})
        
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        application["_id"] = str(application["_id"])
        application["user_id"] = str(application["user_id"])
        application["resume_id"] = str(application["resume_id"])
        application["job_id"] = str(application["job_id"])
        
        return application
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch application status")
    


def my_applications(user_id: str = Query(...)):
    # Validate user_id
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    
    user_obj_id = ObjectId(user_id)
    
    try:
        # Query all applications for this user
        cursor = applications_collection.find({"user_id": user_obj_id})
        
        applications = []
        for app in cursor:
            app["_id"] = str(app["_id"])
            app["user_id"] = str(app["user_id"])
            app["resume_id"] = str(app["resume_id"])
            app["job_id"] = str(app["job_id"])
            applications.append(app)
        
        return applications
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch applications")
    
    
class CandidateDecisionRequest(BaseModel):
    candidate_accept: bool


async def set_candidate_decision(application_id: str, request: CandidateDecisionRequest):
    """
    Set candidate decision (accept/reject) for an application
    POST /api/job/application/{application_id}/decision
    Body: {"candidate_accept": true/false}
    """
    # Validate application_id
    if not ObjectId.is_valid(application_id):
        raise HTTPException(status_code=400, detail="Invalid application_id")
    
    # Check if application exists
    application_doc = applications_collection.find_one({"_id": ObjectId(application_id)})
    if not application_doc:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Update the candidate_accept field
    result = applications_collection.update_one(
        {"_id": ObjectId(application_id)},
        {"$set": {"candidate_accept": request.candidate_accept}}
    )
    
    if result.modified_count == 0 and result.matched_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update decision")
    
    return {
        "success": True,
        "message": "Candidate decision updated successfully",
        "application_id": application_id,
        "candidate_accept": request.candidate_accept
    }


async def get_candidate_decision(application_id: str):
    """
    Get candidate decision for an application
    GET /api/job/application/{application_id}/decision
    Returns: {"candidate_accept": true/false} or {"candidate_accept": null}
    """
    # Validate application_id
    if not ObjectId.is_valid(application_id):
        raise HTTPException(status_code=400, detail="Invalid application_id")
    
    # Find application
    application_doc = applications_collection.find_one({"_id": ObjectId(application_id)})
    if not application_doc:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Get candidate_accept field (returns None if field doesn't exist)
    candidate_accept = application_doc.get("candidate_accept")
    
    return {
        "application_id": application_id,
        "candidate_accept": candidate_accept,
        "decision_exists": candidate_accept is not None
    }