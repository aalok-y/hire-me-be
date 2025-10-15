from fastapi import APIRouter
from controllers.speech_controller import text_to_speech

router = APIRouter(prefix="/api/speech", tags=["tts"])

router.post("/tts")(text_to_speech)

