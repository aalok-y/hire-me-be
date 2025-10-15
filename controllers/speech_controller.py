from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel
from sarvamai import SarvamAI
from sarvamai.play import save
import tempfile
import os
import base64



class TTSRequest(BaseModel):
    text: str
    target_language_code: str = "en-IN"
    model: str = "bulbul:v2"
    speaker: str = "anushka"

client = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))

async def text_to_speech(req: TTSRequest = Body(...)):
    try:
        audio = client.text_to_speech.convert(
            target_language_code=req.target_language_code,
            text=req.text,
            model=req.model,
            speaker=req.speaker
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
            save(audio, tmpfile.name)
            temp_path = tmpfile.name

        with open(temp_path, "rb") as f:
            audio_bytes = f.read()

        os.remove(temp_path)

        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        return {
            "audio_format": "wav",
            "audio_base64": audio_base64,
            "message": "Text-to-speech conversion successful"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sarvam TTS failed: {str(e)}")
