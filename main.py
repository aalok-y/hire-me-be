# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from bson import ObjectId
from config import app
from routes.assessment_routes import  router as assesment_router
from routes.resume_routes import router as resume_router


app.include_router(assesment_router)
app.include_router(resume_router)

@app.get("/")
async def root():
    return {"message": "AI Interview Platform API is running"}


# Run using:
# uvicorn main:app --reload
