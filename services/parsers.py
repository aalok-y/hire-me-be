from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
import pdfplumber
import io
from config import client
from google.genai import types
import re

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
    company_name: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    responsibilities: List[str] = []
    technologies_used: List[str] = []


class Education(BaseModel):
    degree: Optional[str] = None
    major: Optional[str] = None
    university: Optional[str] = None
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


    
class JobDescription(BaseModel):
    job_title: str
    company_name: Optional[str] = None
    job_requirements: List[str]
    required_skills: List[str]
    preferred_skills: Optional[List[str]] = []
    qualifications: List[str]
    experience_required: Optional[str] = None
    job_description: Optional[str] = None
    interview_difficulty: Literal["easy", "moderate", "hard"]






def extract_json_from_gemini_response(text: str) -> str:
    """
    Removes markdown code fences ("```json", "```
    """
    # Remove starting code fence (```json\n or ```
    cleaned = re.sub(r"^```[\w]*\n*", "", text.strip())
    # Remove ending code fence (```
    cleaned = re.sub(r"\n*```$", "", cleaned)
    return cleaned.strip()


def extract_text_from_pdf(pdf_file: bytes) -> str:
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_file)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing PDF: {str(e)}")


async def parse_jd_with_gemini(jd_text: str) -> JobDescription:
    """
    Parses unstructured job description text into structured JobDescription model
    using Gemini API with JSON output.
    """
    try:
        system_prompt = f"""
Extract and structure the following job description into this JSON format:

{{
  "job_title": "string",
  "company_name": "string (optional)",
  "job_requirements": ["list of requirements"],
  "required_skills": ["list of must-have skills"],
  "preferred_skills": ["list of nice-to-have skills (optional)"],
  "qualifications": ["list of educational/professional qualifications"],
  "experience_required": "string (years or level required)",
  "job_description": "string (detailed descriptions or notes)",
  "interview_difficulty": "string (easy, moderate, hard)"
}}


Please output ONLY the JSON matching the above schema.Write None if specific details are not mentionedd
"""
        response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"""Job Description Text: {jd_text}""",
        config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=1),
        system_instruction=system_prompt))
        
        clean_json = extract_json_from_gemini_response(response.text)
        return JobDescription.parse_raw(clean_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini job description parsing failed: {str(e)}")




async def parse_resume_with_gemini(resume_text: str) -> ResumeDocument:
    try:
        prompt = """
You are an expert resume parser. 
Extract and structure all relevant details from the following resume strictly in this JSON format. 
If a detail is missing in the resume, return null for that field or an empty array for lists. 
Do not include any explanation, markdown, or text outside the JSON.

{
  "resume": {
    "header": {
      "full_name": "string",
      "contact_information": {
        "email": "string",
        "phone": "string",
        "linkedIn": "string",
        "github": "string",
        "portfolio_website": "string"
      }
    },
    "summary": "string (Brief professional summary or objective statement)",
    "skills": [
      "list of technical skills (e.g., programming languages, tools, frameworks)"
    ],
    "experience": [
      {
        "job_title": "string",
        "company_name": "string",
        "location": "string",
        "start_date": "string (month and year)",
        "end_date": "string (month and year or 'Present')",
        "responsibilities": [
          "list of key responsibilities and achievements"
        ],
        "technologies_used": [
          "list of technologies/tools used in the role"
        ]
      }
    ],
    "education": [
      {
        "degree": "string",
        "major": "string",
        "university": "string",
        "location": "string",
        "start_date": "string (year)",
        "end_date": "string (year or 'Present')",
        "additional_info": "string (e.g., GPA, relevant coursework)"
      }
    ],
    "projects": [
      {
        "project_name": "string",
        "description": "string",
        "technologies_used": [
          "list of relevant technologies"
        ],
        "role": "string (optional)",
        "link": "string (optional, e.g., GitHub URL)"
      }
    ],
    "certifications": [
      {
        "certification_name": "string",
        "issuing_organization": "string",
        "issue_date": "string (month and year)",
        "expiration_date": "string (optional)"
      }
    ],
    "awards_and_honors": [
      {
        "title": "string",
        "issuer": "string",
        "date_received": "string"
      }
    ],
    "languages": [
      {
        "language": "string",
        "proficiency": "string"
      }
    ],
    "interests": [
      "list of personal or professional interests"
    ]
  }
}

Only output the filled JSON matching the schema above, with all available fields mapped from the resume below. Fill array fields with empty arrays if not present. Use null for missing string values.

"""

        response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"""Resume Text: {resume_text}""",
        config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=1),
        system_instruction=prompt))
        
        # Parse to ResumeDocument
        print("gemini response: ",response.text)
        clean_json = extract_json_from_gemini_response(response.text)
        return ResumeDocument.parse_raw(clean_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini parsing failed: {str(e)}")

