from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from typing import Dict

# Constants
UPLOAD_DIR = "uploaded_voices"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="Voice Monitor Backend API",
    description="API for voice enrollment/upload and monitoring voice matches.",
    version="0.1.0",
    openapi_tags=[
        {"name": "voice", "description": "User voice upload and enrollment API"}
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    """Health check endpoint.
    Returns {"message": "Healthy"} if server is up.
    """
    return {"message": "Healthy"}

# PUBLIC_INTERFACE
@app.post("/enroll/voice", response_model=None, tags=["voice"], summary="Upload user voice for enrollment", description="Upload a voice/audio file for user enrollment. Supports .wav, .mp3 etc.")
async def upload_voice(
    file: UploadFile = File(..., description="Audio file for enrollment (wav, mp3, etc.)"),
):
    """
    Upload a voice/audio file for enrollment.

    Args:
        file (UploadFile): Audio file, accepted formats: wav, mp3.

    Returns:
        JSON with upload status and filename.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".wav", ".mp3", ".m4a", ".opus", ".ogg"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    save_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(save_path, "wb") as out_file:
            while chunk := await file.read(8192):
                out_file.write(chunk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed saving file: {str(e)}")

    return JSONResponse(
        content={
            "status": "success",
            "filename": file.filename,
            "detail": "File uploaded. Enrollment in progress (future)."
        },
        status_code=201
    )
