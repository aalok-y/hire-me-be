
from fastapi import HTTPException,Body
from bson import ObjectId
from google import genai
from pydantic import BaseModel
from typing import List, Dict, Any
from utils.pymango_wrappers import async_insert_one,async_find_one 
from config import resumes_collection, assessments_collection, jds_collection
from config import client

class ChatTurn(BaseModel):
    role: str  # 'model' or 'user'
    content: str  # message content

class AssessCandidateInterviewRequest(BaseModel):
    job_id: str
    resume_id: str
    chat_history: List[ChatTurn]  # ordered conversation turns between model and candidate
    difficulty: str  # e.g., 'easy', 'moderate', 'hard'

async def assess_candidate_interview(request: AssessCandidateInterviewRequest):
    

    # Validate object IDs
    if not ObjectId.is_valid(request.job_id):
        raise HTTPException(status_code=400, detail="Invalid job_id")
    if not ObjectId.is_valid(request.resume_id):
        raise HTTPException(status_code=400, detail="Invalid resume_id")

    # Fetch structured job description and resume from DB (replace with your async DB calls)
    job_desc_doc = await async_find_one(jds_collection, {"_id": ObjectId(request.job_id)})
    if not job_desc_doc:
        raise HTTPException(status_code=404, detail="Job description not found")
    resume_doc = await async_find_one(resumes_collection, {"_id": ObjectId(request.resume_id)})
    if not resume_doc:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Remove internal DB fields
    for key in ["_id", "original_filename", "raw_text"]:
        job_desc_doc.pop(key, None)
        resume_doc.pop(key, None)

    # Convert docs to JSON strings (you may need json.dumps if needed)
    import json
    job_desc_json = json.dumps(job_desc_doc)
    resume_json = json.dumps(resume_doc)

    # Prepare system prompt with instructions for Gemini
    SYSTEM_PROMPT = """
You are an expert recruiter AI assessing a candidate for a software engineering role. 
Based on the structured job description, structured candidate resume, and the entire chat history between candidate and model, provide:
1. A summary of the candidate's capabilities, strengths, and weaknesses.
2. A final fitment rating: Best Fit, Moderate Fit, or Worst Fit.
3. A concise justification for the final rating.

Be objective and thorough. Output a strict JSON object with these fields: 
{
  "capabilities_summary": "string",
  "fitment_rating": "Best Fit|Moderate Fit|Worst Fit",
  "justification": "string"
}
Only return this JSON. No extra commentary.
"""

    # Build prompt contents including chat history as concatenated turns
    chat_history_text = ""
    for turn in request.chat_history:
        speaker = "Interviewer" if turn.role == "model" else "Candidate"
        chat_history_text += f"{speaker}: {turn.content}\n"

    contents = (
        f"Job Description:\n{job_desc_json}\n\n"
        f"Candidate Resume:\n{resume_json}\n\n"
        f"Difficulty Level: {request.difficulty}\n\n"
        f"Conversation History:\n{chat_history_text}"
    )

    # Call Gemini API to generate assessment
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=genai.types.GenerateContentConfig(
            thinking_config=genai.types.ThinkingConfig(thinking_budget=2),
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json"
        )
    )

    print("Gemini response, candidate assessment:", response.text)

    # Parse the JSON output and return
    from pydantic import parse_raw_as
    class AssessmentResult(BaseModel):
        capabilities_summary: str
        fitment_rating: str
        justification: str

    assessment = AssessmentResult.parse_raw(response.text)
    return assessment


class CandidateTurn(BaseModel):
    question: str      # Previous interview question
    answer: str        # Candidate's answer
    timestamp: str     # ISO timestamp when the answer was submitted

class InterviewRequest(BaseModel):
    resume: dict
    job_description: dict
    difficulty: str   # "easy", "moderate", "hard"
    turns: List[CandidateTurn]  # List of prior question/answer/timestamps
    duration_seconds: int       # Elapsed interview time in seconds


async def generate_next_question(
    request: InterviewRequest = Body(...)
):

    client = genai.Client()
    SYSTEM_PROMPT = """
You are an expert technical interviewer for software engineering roles conducting a virtual interview lasting 8 minutes.

Your objective is to generate one targeted, role-specific interview question per turn, using the following context:
- The structured candidate resume including skills, experience, education, and projects
- The structured job description detailing role responsibilities, required skills, and qualifications
- The specified interview difficulty level (easy, moderate, hard)
- The candidate's prior answers and their timestamps, maintaining a full chronological history of the session

Guidelines:
- Begin with easier questions and gradually increase difficulty aligned to the specified level.
- Tailor each question specifically to both the candidate's background and the job requirements.
- Leverage semantic understanding of candidate answers and timestamps to adapt follow-up questions.
- Monitor the total elapsed interview time, and conclude questioning exactly or shortly after 8 minutes.
- Respond with the next interview question only; do not include explanations, commentary, or candidate answers.
- Ensure questions cover technical skills, problem-solving abilities, behavioral and situational topics as relevant.
- Avoid repetition—each question should build on previous dialogue to assess new facets.
- Use timestamps as critical contextual signals to manage pacing and adaptiveness.
- Maintain clarity and precision appropriate for a real-world technical interview setting.

Stop generating new questions once the 8-minute interview duration is reached.

Respond ONLY with the next question in natural language suitable for a technical candidate.

"""
    # Prepare chat history
    chat_history = [
        # System instruction
        {"role": "model", "parts": [{"text": SYSTEM_PROMPT}]},
        # Provide resume+JD context to model before turns
        {"role": "user", "parts": [{"text":
            f"Candidate resume:\n{request.resume}\nJob description:\n{request.job_description}\nDifficulty: {request.difficulty}"
        }]}
    ]
    # Add all previous turns to context
    for turn in request.turns:
        chat_history.append({"role": "model", "parts": [{"text": turn.question}]})
        chat_history.append({"role": "user", "parts": [{"text":
            f"Answer [{turn.timestamp}]: {turn.answer}"
        }]})
    # Add current duration context
    chat_history.append({"role": "user", "parts": [
        {"text": f"Interview elapsed time: {request.duration_seconds} seconds"}
    ]})
    # Ask for next question
    chat_history.append({"role": "user", "parts": [
        {"text": "Generate the next interview question for the candidate."}
    ]})
    # Create chat session and get response
    chat = client.chats.create(model="gemini-2.5-flash", history=chat_history)
    response = chat.send_message("Next question, please.")
    return {"next_question": response.text}
