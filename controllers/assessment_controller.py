from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from bson import ObjectId
from utils.pymango_wrappers import async_insert_one,async_find_one 
from config import resumes_collection, assessments_collection, jds_collection
from config import app
from services.candidate_assessment import assess_candidate_fitment
from services.parsers import extract_json_from_gemini_response
from fastapi.concurrency import run_in_threadpool


class JobDescription(BaseModel):
    job_title: str
    company_name: Optional[str] = None
    job_requirements: List[str]
    required_skills: List[str]
    preferred_skills: Optional[List[str]] = []
    qualifications: List[str]
    experience_required: Optional[str] = None
    job_description: Optional[str] = None



class ContactInformation(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    linkedIn: Optional[str] = None
    github: Optional[str] = None
    portfolio_website: Optional[str] = None


class Header(BaseModel):
    full_name: str
    contact_information: ContactInformation


class Experience(BaseModel):
    job_title: str
    company_name: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    responsibilities: List[str] = []
    technologies_used: List[str] = []


class Education(BaseModel):
    degree: str
    major: Optional[str] = None
    university: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    additional_info: Optional[str] = None


class Project(BaseModel):
    project_name: str
    description: str
    technologies_used: List[str] = []
    role: Optional[str] = None
    link: Optional[str] = None


class Certification(BaseModel):
    certification_name: str
    issuing_organization: str
    issue_date: Optional[str] = None
    expiration_date: Optional[str] = None


class AwardHonor(BaseModel):
    title: str
    issuer: str
    date_received: Optional[str] = None


class Language(BaseModel):
    language: str
    proficiency: str


class Resume(BaseModel):
    header: Header
    summary: Optional[str] = None
    skills: List[str] = []
    experience: List[Experience] = []
    education: List[Education] = []
    projects: List[Project] = []
    certifications: List[Certification] = []
    awards_and_honors: List[AwardHonor] = []
    languages: List[Language] = []
    interests: List[str] = []



class ResumeDocument(BaseModel):
    resume: Resume

class AssessmentResult(BaseModel):
    candidate_name: str
    job_title: str
    overall_match_score: float = Field(..., ge=0, le=100)
    skills_match_score: float = Field(..., ge=0, le=100)
    experience_match_score: float = Field(..., ge=0, le=100)
    education_match_score: float = Field(..., ge=0, le=100)
    matched_skills: List[str]
    missing_skills: List[str]
    strengths: List[str]
    weaknesses: List[str]
    recommendation: str
    detailed_analysis: str



# ------------------ Routes ------------------



async def get_assessment(assessment_id: str):
    if not ObjectId.is_valid(assessment_id):
        raise HTTPException(status_code=400, detail="Invalid assessment ID")
    assessment = await async_find_one(
        assessments_collection, {"_id": ObjectId(assessment_id)}
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    assessment["_id"] = str(assessment["_id"])
    return assessment




async def assess_candidate(
    resume_id: str = Body(..., embed=True), 
    job_id: str = Body(..., embed=True)
):
    if not ObjectId.is_valid(resume_id):
        raise HTTPException(status_code=400, detail="Invalid resume ID")
    if not ObjectId.is_valid(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")

    try:
        resume_data = await run_in_threadpool(
            resumes_collection.find_one, {"_id": ObjectId(resume_id)}
        )
        if not resume_data:
            raise HTTPException(status_code=404, detail="Resume not found")

        job_data = await run_in_threadpool(
            jds_collection.find_one, {"_id": ObjectId(job_id)}
        )
        if not job_data:
            raise HTTPException(status_code=404, detail="Job description not found")

        # Remove MongoDB internal fields not part of Pydantic models
        for key in ["_id", "original_filename", "raw_text"]:
            resume_data.pop(key, None)
            job_data.pop(key, None)

        resume_doc = ResumeDocument(**resume_data)
        job_doc = JobDescription(**job_data)

        # Call Gemini API for fitment assessment (returns raw response with .text)
        assessment = await assess_candidate_fitment(job_doc, resume_doc)


        # Prepare assessment dict for DB insertion
        assessment_data = assessment.model_dump()
        assessment_data["resume_id"] = resume_id
        assessment_data["job_id"] = job_id
        assessment_data["job_description"] = job_doc.model_dump()

        result = await run_in_threadpool(
            assessments_collection.insert_one, assessment_data
        )

        return {
            "message": "Assessment completed",
            "assessment_id": str(result.inserted_id),
            "assessment": assessment.model_dump(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")


