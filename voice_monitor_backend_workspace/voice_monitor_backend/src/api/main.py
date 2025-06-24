from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import json
import hashlib
from typing import Dict

# Constants
UPLOAD_DIR = "uploaded_voices"
EMBEDDING_FILE = os.path.join(UPLOAD_DIR, "enrollments.json")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# Simple persistence for demonstration (would be DB in prod)
def load_enrollments() -> Dict[str, dict]:
    if not os.path.exists(EMBEDDING_FILE):
        return {}
    with open(EMBEDDING_FILE, "r") as f:
        return json.load(f)


def save_enrollments(data: Dict[str, dict]) -> None:
    with open(EMBEDDING_FILE, "w") as f:
        json.dump(data, f)


def simulate_voice_embedding(filepath: str) -> str:
    """Fake a 'voice embedding' by hashing the file. Replace with real model in production."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""


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
@app.post(
    "/enroll/voice",
    response_model=None,
    tags=["voice"],
    summary="Upload user voice for enrollment",
    description="Upload a voice/audio file for user enrollment. Supports .wav, .mp3 etc."
)
async def upload_voice(
    file: UploadFile = File(..., description="Audio file for enrollment (wav, mp3, etc.)"),
    user_id: str = Query(..., description="Unique identifier for the user"),
):
    """
    Upload a voice/audio file for enrollment.

    Args:
        file (UploadFile): Audio file, accepted formats: wav, mp3.
        user_id (str): Unique user identifier.

    Returns:
        JSON with upload status and filename.
    """
    # File validation and save
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".wav", ".mp3", ".m4a", ".opus", ".ogg"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    safe_filename = f"{user_id}_{file.filename}"
    save_path = os.path.join(UPLOAD_DIR, safe_filename)
    try:
        with open(save_path, "wb") as out_file:
            while chunk := await file.read(8192):
                out_file.write(chunk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed saving file: {str(e)}")

    # Simulate embedding and store enrollment
    embedding = simulate_voice_embedding(save_path)
    enrollments = load_enrollments()
    enrollments[user_id] = {
        "filename": safe_filename,
        "embedding": embedding
    }
    save_enrollments(enrollments)

    return JSONResponse(
        content={
            "status": "success",
            "filename": safe_filename,
            "detail": "File uploaded. Enrollment completed (simulated).",
        },
        status_code=201
    )

# PUBLIC_INTERFACE
@app.get(
    "/enroll/status",
    tags=["voice"],
    summary="Query user enrollment status",
    description="Get enrollment status for a user (has enrolled voice profile or not)."
)
def enrollment_status(
    user_id: str = Query(..., description="Unique identifier for the user"),
):
    """
    Get enrollment status for a user.

    Args:
        user_id (str): Unique user identifier.

    Returns:
        JSON status: 'enrolled' + basic info, or 'not_enrolled'
    """
    enrollments = load_enrollments()
    if user_id in enrollments:
        enrollment_data = enrollments[user_id]
        return {
            "status": "enrolled",
            "filename": enrollment_data.get("filename", ""),
            "has_embedding": bool(enrollment_data.get("embedding")),
        }
    else:
        return {
            "status": "not_enrolled"
        }
