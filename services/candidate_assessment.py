from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from google.genai import types
from config import client



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


class JobDescription(BaseModel):
    job_title: str
    company_name: Optional[str] = None
    job_requirements: List[str]
    required_skills: List[str]
    preferred_skills: Optional[List[str]] = []
    qualifications: List[str]
    experience_required: Optional[str] = None
    job_description: Optional[str] = None


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





async def assess_candidate_fitment(
    job_desc: JobDescription, resume_doc: ResumeDocument
) -> AssessmentResult:
    try:
        job_desc_json = job_desc.model_dump_json()
        resume_json = resume_doc.model_dump_json()
        prompt = f"""
Evaluate candidate fitment for the given job description and resume JSON.

Return output strictly as valid JSON conforming to the following schema:

class AssessmentResult(BaseModel):
    candidate_name: str
    job_title: str
    overall_match_score: float  # range 0–100
    skills_match_score: float   # range 0–100
    experience_match_score: float  # range 0–100
    education_match_score: float   # range 0–100
    matched_skills: List[str]
    missing_skills: List[str]
    strengths: List[str]
    weaknesses: List[str]
    recommendation: str  # concise hiring recommendation (e.g. "Strong Fit", "Moderate Fit", "Weak Fit")
    detailed_analysis: str  # paragraph explaining reasoning across all categories

Instructions:
- Compare job requirements and resume objectively.
- Use evidence from the resume to justify scores and lists.
- Ensure JSON is syntactically valid and fully populates all fields.
- Do not include extra commentary or text outside the JSON.

"""
        response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"""Job Description: {job_desc_json} Candidate Resume: {resume_json}""",
        config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=1),system_instruction=prompt,response_mime_type="application/json"),
        )
        print("gemini response, candidate fit: ", response.text)
        return AssessmentResult.model_validate_json(response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")

