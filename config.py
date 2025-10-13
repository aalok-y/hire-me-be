from dotenv import load_dotenv
from fastapi import FastAPI
import pymongo
from google import genai
import os




# Load environment variables
load_dotenv()

# Configure Gemini API
client = genai.Client()


app = FastAPI(title="AI Interview Platform API")

# MongoDB connection string from environment
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client.interview_platform
resumes_collection = db.resumes
assessments_collection = db.assessments
jds_collection = db.jds



