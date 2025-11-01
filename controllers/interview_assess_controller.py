
from fastapi import HTTPException,Body
from bson import ObjectId
from google import genai
from pydantic import BaseModel
from typing import List, Optional
from utils.pymango_wrappers import async_insert_one,async_find_one 
from config import resumes_collection, assessments_collection, jds_collection, interview_assessments_collection, applications_collection, interviews_collection
from config import client
from bson import json_util
from fastapi.responses import JSONResponse
from bson import json_util  
import json
import time
from json_repair import repair_json


class ChatTurn(BaseModel):
    role: str  # 'model' or 'user'
    content: str  # message content

class AssessCandidateInterviewRequest(BaseModel):
    job_id: str
    resume_id: str
    application_id: str
    chat_history: List[ChatTurn]  # ordered conversation turns between model and candidate
    difficulty: str  # e.g., 'easy', 'moderate', 'hard'

class AssessmentResult(BaseModel):
    capabilities_summary: str
    fitment_rating: str
    justification: str
    video_analysis_insights: Optional[str] = None  


# async def assess_candidate_interview(request: AssessCandidateInterviewRequest):
    

#     # Validate object IDs
#     if not ObjectId.is_valid(request.job_id):
#         raise HTTPException(status_code=400, detail="Invalid job_id")
#     if not ObjectId.is_valid(request.resume_id):
#         raise HTTPException(status_code=400, detail="Invalid resume_id")

#     # Fetch structured job description and resume from DB (replace with your async DB calls)
#     job_desc_doc = await async_find_one(jds_collection, {"_id": ObjectId(request.job_id)})
#     if not job_desc_doc:
#         raise HTTPException(status_code=404, detail="Job description not found")
#     resume_doc = await async_find_one(resumes_collection, {"_id": ObjectId(request.resume_id)})
#     if not resume_doc:
#         raise HTTPException(status_code=404, detail="Resume not found")

#     # Remove internal DB fields
#     for key in ["_id", "original_filename", "raw_text"]:
#         job_desc_doc.pop(key, None)
#         resume_doc.pop(key, None)

#     # Convert docs to JSON strings (you may need json.dumps if needed)
#     import json
#     job_desc_json = json_util.dumps(job_desc_doc)
#     resume_json = json.dumps(resume_doc)

#     # Prepare system prompt with instructions for Gemini
#     SYSTEM_PROMPT = """
# You are an expert recruiter AI assessing a candidate for a software engineering role. 
# Based on the structured job description, structured candidate resume, and the entire chat history between candidate and model, provide:
# 1. A summary of the candidate's capabilities, strengths, and weaknesses.
# 2. A final fitment rating: Best Fit, Moderate Fit, or Worst Fit.
# 3. A concise justification for the final rating.

# Be objective and thorough. Output a strict JSON object with these fields: 
# {
#   "capabilities_summary": "string",
#   "fitment_rating": "Best Fit|Moderate Fit|Worst Fit",
#   "justification": "string"
# }
# Only return this JSON. No extra commentary.
# Be thorough and strict. If response by the candidate does not fit the industry standards then don't consider that answer and descreseas overall rating.
# While assessing give priority to candidate's response to questions over their resume.
# """

#     # Build prompt contents including chat history as concatenated turns
#     chat_history_text = ""
#     for turn in request.chat_history:
#         speaker = "Interviewer" if turn.role == "model" else "Candidate"
#         chat_history_text += f"{speaker}: {turn.content}\n"

#     contents = (
#         f"Job Description:\n{job_desc_json}\n\n"
#         f"Candidate Resume:\n{resume_json}\n\n"
#         f"Difficulty Level: {request.difficulty}\n\n"
#         f"Conversation History:\n{chat_history_text}"
#     )

#     # Call Gemini API to generate assessment
#     response = client.models.generate_content(
#         model="gemini-2.5-flash",
#         contents=contents,
#         config=genai.types.GenerateContentConfig(
#             thinking_config=genai.types.ThinkingConfig(thinking_budget=2),
#             system_instruction=SYSTEM_PROMPT,
#             response_mime_type="application/json"
#         )
#     )

#     print("Gemini response, candidate assessment:", response.text)

#     # Parse the JSON output and return
#     class AssessmentResult(BaseModel):
#         capabilities_summary: str
#         fitment_rating: str
#         justification: str

#     assessment = AssessmentResult.model_validate_json(response.text)
#     return assessment


async def assess_candidate_interview(request: AssessCandidateInterviewRequest):
    """Assess candidate interview including video analysis"""
    
    # Validate object IDs
    if not ObjectId.is_valid(request.job_id):
        raise HTTPException(status_code=400, detail="Invalid job_id")
    if not ObjectId.is_valid(request.resume_id):
        raise HTTPException(status_code=400, detail="Invalid resume_id")
    if not ObjectId.is_valid(request.application_id):
        raise HTTPException(status_code=400, detail="Invalid application_id")

    # Fetch job description and resume
    job_desc_doc = jds_collection.find_one({"_id": ObjectId(request.job_id)})
    if not job_desc_doc:
        raise HTTPException(status_code=404, detail="Job description not found")
    
    resume_doc = resumes_collection.find_one({"_id": ObjectId(request.resume_id)})
    if not resume_doc:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Fetch interview data (video analysis + chat) from interviews_collection
    application_doc = applications_collection.find_one({"_id": ObjectId(request.application_id)})
    if not application_doc:
        raise HTTPException(status_code=404, detail="Application not found")
    
    interview_id = application_doc.get("interview_id")
    video_analysis = None
    
    if interview_id:
        interview_doc = interviews_collection.find_one({"_id": ObjectId(interview_id)})
        if interview_doc:
            video_analysis_data = interview_doc.get("video_analysis", {})
            video_analysis = {
                "audio_analysis": video_analysis_data.get("combined_audio_analysis", {}),
                "video_analysis": video_analysis_data.get("combined_video_analysis", {})
            }

    # Remove internal DB fields
    for key in ["_id", "original_filename", "raw_text"]:
        job_desc_doc.pop(key, None)
        resume_doc.pop(key, None)

    # Use bson.json_util instead of json
    job_desc_json = json_util.dumps(job_desc_doc)
    resume_json = json_util.dumps(resume_doc)


    # Prepare enhanced system prompt
    SYSTEM_PROMPT = """
You are an expert recruiter AI assessing a candidate for a software engineering role. 
Based on the structured job description, structured candidate resume, chat history, and VIDEO INTERVIEW ANALYSIS, provide:

1. A summary of the candidate's capabilities, strengths, and weaknesses
2. Assessment of communication skills based on video analysis (speaking rate, pauses, confidence)
3. Assessment of emotional stability and engagement based on facial emotion analysis
4. A final fitment rating: Best Fit, Moderate Fit, or Worst Fit
5. A concise justification for the final rating

**Video Analysis Interpretation Guidelines:**
- Speaking Rate: 120-150 WPM is normal, >180 WPM may indicate nervousness or rushed speech
- Pause Ratio: 10-20% is healthy, >30% may indicate uncertainty
- Dominant Emotion: "neutral" with occasional positive emotions is ideal for professional interviews
- Frequent emotion shifts may indicate nervousness or lack of composure
- Pitch variability indicates expressiveness (good), monotone indicates lack of engagement

Be objective and thorough. Output a strict JSON object with these fields: 
{
  "capabilities_summary": "string",
  "fitment_rating": "Best Fit|Moderate Fit|Worst Fit",
  "justification": "string",
  "video_analysis_insights": "string (summary of communication and presentation skills based on video)"
}

Only return this JSON. No extra commentary.
Be thorough and strict. If response by the candidate does not fit industry standards, decrease overall rating.
While assessing, give priority to candidate's response to questions over their resume.
Consider video analysis for communication skills, confidence, and professional presentation.
"""

    # Build chat history
    chat_history_text = ""
    for turn in request.chat_history:
        speaker = "Interviewer" if turn.role == "model" else "Candidate"
        chat_history_text += f"{speaker}: {turn.content}\n"

    # Build video analysis summary
    video_analysis_text = "Video Analysis: Not Available"
    
    if video_analysis:
        audio = video_analysis.get("audio_analysis", {})
        video = video_analysis.get("video_analysis", {})
        
        metadata = audio.get("metadata", {})
        transcription = audio.get("transcription", {})
        voice_mod = audio.get("voice_modulation", {})
        
        persons = video.get("persons_detected", 0)
        person_data = video.get("person_1", {}) if persons > 0 else {}
        
        video_analysis_text = f"""
Video & Audio Analysis:

Audio Metrics:
- Duration: {metadata.get('duration_sec', 0):.1f} seconds
- Speaking Time: {metadata.get('speech_time_sec', 0):.1f} seconds
- Pause Time: {metadata.get('total_pause_sec', 0):.1f} seconds
- Speech Ratio: {metadata.get('speech_to_total_ratio', 0):.2%}
- Word Count: {transcription.get('word_count', 0)}
- Speaking Rate: {transcription.get('speaking_rate_wpm', 0):.1f} WPM
- Average Volume: {voice_mod.get('avg_volume_rms', 0):.4f}
- Pitch Mean: {voice_mod.get('mean_pitch_hz', 0):.1f} Hz
- Pitch Variability: {voice_mod.get('pitch_variability_std_dev_hz', 0):.1f} Hz

Visual Analysis:
- Persons Detected: {persons}
- Age Range: {person_data.get('age_range', {}).get('min', 'N/A')}-{person_data.get('age_range', {}).get('max', 'N/A')} (avg: {person_data.get('age_range', {}).get('average', 'N/A')})
- Gender: {person_data.get('gender', 'N/A')}
- Dominant Emotion: {person_data.get('dominant_emotion_overall', 'N/A')}
- Emotion Distribution: {json.dumps(person_data.get('emotion_distribution_percent', {}))}
- Emotion Shifts Count: {len(person_data.get('notable_emotion_shifts', []))}
"""

    # Combine all information
    contents = (
        f"Job Description:\n{job_desc_json}\n\n"
        f"Candidate Resume:\n{resume_json}\n\n"
        f"Difficulty Level: {request.difficulty}\n\n"
        f"Conversation History:\n{chat_history_text}\n\n"
        f"Video Analysis:\n{video_analysis_text}"
    )

    # Call Gemini API
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=genai.types.GenerateContentConfig(
            thinking_config=genai.types.ThinkingConfig(thinking_budget=2),
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json"
        )
    )

    print("Gemini raw response (assess_candidate):", response.text)

    try:
        repaired_json = repair_json(response.text)
        assessment = AssessmentResult.model_validate_json(repaired_json)
    except Exception as e:
        print(f"Failed to parse even after repair. Raw response: {response.text}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to parse Gemini response: {str(e)}"
        )
        

    # Store the final assessment in interview_assessments_collection
    assessment_doc = {
        "application_id": ObjectId(request.application_id),
        "job_id": ObjectId(request.job_id),
        "resume_id": ObjectId(request.resume_id),
        "interview_id": ObjectId(interview_id) if interview_id else None,
        "assessment": assessment.dict(),
        "difficulty": request.difficulty,
        "video_analysis_included": video_analysis is not None,
        "created_at": time.time()
    }

    # Insert final assessment
    result = interview_assessments_collection.insert_one(assessment_doc)
    assessment_id = str(result.inserted_id)

    print(f"[Assessment] Stored final assessment: {assessment_id}")

    
    return {
        "assessment_id": assessment_id,
        "capabilities_summary": assessment.capabilities_summary,
        "fitment_rating": assessment.fitment_rating,
        "justification": assessment.justification,
        "video_analysis_insights": assessment.video_analysis_insights
    }



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
You are an expert technical interviewer for software engineering roles conducting a virtual interview lasting 7 minutes.

Your objective is to generate one targeted, role-specific interview question per turn, using the following context:
- The structured candidate resume including skills, experience, education, and projects
- The structured job description detailing role responsibilities, required skills, and qualifications
- The specified interview difficulty level (easy, moderate, hard)
- The candidate's prior answers and their timestamps, maintaining a full chronological history of the session

Guidelines:
- Begin with easier questions and gradually increase difficulty aligned to the specified level.
- Tailor each question specifically to both the candidate's background and the job requirements.
- Leverage semantic understanding of candidate answers and timestamps to adapt follow-up questions.
- Monitor the total elapsed interview time, and conclude questioning exactly or shortly after 7 minutes.
- Respond with the next interview question only; do not include explanations, commentary, or candidate answers.
- Ensure questions cover technical skills, problem-solving abilities, behavioral and situational topics as relevant.
- Avoid repetition—each question should build on previous dialogue to assess new facets.
- Use timestamps as critical contextual signals to manage pacing and adaptiveness.
- Maintain clarity and precision appropriate for a real-world technical interview setting.

Stop generating new questions once the 7-minute interview duration is reached.

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


async def get_interview_assessment(application_id: str):
    """
    Fetch complete interview assessment including chat history, video analysis, and final assessment
    """
    # Validate application_id
    if not ObjectId.is_valid(application_id):
        raise HTTPException(status_code=400, detail="Invalid application_id")
    
    # Fetch application
    application_doc = applications_collection.find_one({"_id": ObjectId(application_id)})
    if not application_doc:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Get status
    status = application_doc.get("status", "unknown")
    
    # Initialize response
    response_data = {
        "application_id": application_id,
        "status": status,
        "interview_data": None,
        "final_assessment": None
    }
    
    # Fetch interview data (chat history + video analysis)
    interview_id = application_doc.get("interview_id")
    if interview_id:
        interview_doc = interviews_collection.find_one({"_id": ObjectId(interview_id)})
        if interview_doc:
            response_data["interview_data"] = {
                "interview_id": str(interview_doc["_id"]),
                "chat_history": interview_doc.get("chat_history", []),
                "video_analysis": interview_doc.get("video_analysis", {}),
                "processed_at": interview_doc.get("processed_at")
            }
    
    # Fetch FINAL assessment (combined resume + interview)
    final_assessment_id = application_doc.get("final_assessment_id")
    if final_assessment_id:
        assessment_doc = interview_assessments_collection.find_one({"_id": ObjectId(final_assessment_id)})
        if assessment_doc:
            response_data["final_assessment"] = {
                "assessment_id": str(assessment_doc["_id"]),
                "assessment": assessment_doc.get("assessment", {}),
                "difficulty": assessment_doc.get("difficulty"),
                "video_analysis_included": assessment_doc.get("video_analysis_included", False),
                "created_at": assessment_doc.get("created_at")
            }
    
    return JSONResponse(content=response_data)

async def get_assessment_summary(application_id: str):
    """
    Fetch only the final assessment summary (without full chat history or video data)
    """
    # Validate application_id
    if not ObjectId.is_valid(application_id):
        raise HTTPException(status_code=400, detail="Invalid application_id")
    
    # Fetch application
    application_doc = applications_collection.find_one({"_id": ObjectId(application_id)})
    if not application_doc:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Get status
    status = application_doc.get("status", "unknown")
    
    # Get FINAL assessment_id (changed from "assessment_id")
    final_assessment_id = application_doc.get("final_assessment_id")
    
    # Return status without assessment if not ready yet
    if not final_assessment_id:
        return JSONResponse(content={
            "application_id": application_id,
            "status": status,
            "assessment_ready": False,
            "message": "Final assessment not yet available. Interview may still be processing."
        })
    
    # Fetch final assessment
    assessment_doc = interview_assessments_collection.find_one({"_id": ObjectId(final_assessment_id)})
    
    # Handle case where assessment_id exists but document is missing
    if not assessment_doc:
        return JSONResponse(content={
            "application_id": application_id,
            "status": status,
            "assessment_ready": False,
            "message": "Assessment document not found. This may indicate a processing error."
        })
    
    # Return only assessment data
    return JSONResponse(content={
        "application_id": application_id,
        "assessment_id": str(assessment_doc["_id"]),
        "status": status,
        "assessment_ready": True,
        "assessment": assessment_doc.get("assessment", {}),
        "difficulty": assessment_doc.get("difficulty"),
        "created_at": assessment_doc.get("created_at")
    })
