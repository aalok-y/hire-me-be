from dotenv import load_dotenv
from fastapi import FastAPI
import pymongo
from google import genai
import os
# main.py

from fastapi.middleware.cors import CORSMiddleware



# Load environment variables
load_dotenv()

# Configure Gemini API
client = genai.Client()


app = FastAPI(title="AI Interview Platform API")

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # allows requests from these origins
    allow_credentials=True,
    allow_methods=["*"],    # allow all methods (GET, POST, etc.)
    allow_headers=["*"],    # allow all headers
)


# MongoDB connection string from environment
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client.interview_platform
users_collection = db.users
resumes_collection = db.resumes
assessments_collection = db.assessments
jds_collection = db.jds
interviews_collection = db.interviews
applications_collection = db.applications


users_collection.create_index("email", unique=True)


