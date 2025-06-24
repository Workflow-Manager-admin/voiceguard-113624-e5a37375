from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import json
from typing import Dict

# Import Speechbrain and torch
import torch
from speechbrain.pretrained import EncoderClassifier

# Constants
UPLOAD_DIR = "uploaded_voices"
EMBEDDING_FILE = os.path.join(UPLOAD_DIR, "enrollments.json")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Speechbrain model setup as singleton (loaded lazily)
_classifier = None


def get_speechbrain_classifier():
    """
    Loads (if not already loaded) the speechbrain ECAPA-voxceleb classifier.
    Avoids reloading on each request.
    """
    global _classifier
    if _classifier is None:
        # Model path can be overridden by env var if pre-downloaded,
        # else automatically downloads from HuggingFace
        _classifier = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            run_opts={"device": "cuda" if torch.cuda.is_available() else "cpu"}
        )
    return _classifier


def compute_embedding(file_path: str):
    """
    Returns a numpy array representation of the Speechbrain ECAPA-voxceleb
    embedding for the provided audio file.
    """
    classifier = get_speechbrain_classifier()
    signal, fs = classifier.load_audio(file_path)
    # Batched input expected shape (batch, time)
    embedding = classifier.encode_batch(signal.unsqueeze(0))
    # Convert Torch tensor to list for JSON serialization
    embedding_np = embedding.squeeze().detach().cpu().numpy().tolist()
    return embedding_np


# Simple persistence for demonstration (would be DB in prod)
def load_enrollments() -> Dict[str, dict]:
    if not os.path.exists(EMBEDDING_FILE):
        return {}
    with open(EMBEDDING_FILE, "r") as f:
        return json.load(f)


def save_enrollments(data: Dict[str, dict]) -> None:
    with open(EMBEDDING_FILE, "w") as f:
        json.dump(data, f)


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
    Upload a voice/audio file for enrollment using Speechbrain ECAPA-voxceleb to compute speaker
    embedding.

    Args:
        file (UploadFile): Audio file, accepted formats: wav, mp3, m4a, opus, ogg.
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

    # Compute real voiceprint embedding and store enrollment
    try:
        embedding = compute_embedding(save_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Embedding computation failed: {str(e)}"
        )
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
            "detail": (
                "File uploaded. Enrollment with Speechbrain embedding completed."
            ),
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
        # Since we now store a list/array embedding, check that it is a non-empty list
        has_embedding = (
            enrollment_data.get("embedding") is not None
            and isinstance(enrollment_data["embedding"], list)
            and len(enrollment_data["embedding"]) > 0
        )
        return {
            "status": "enrolled",
            "filename": enrollment_data.get("filename", ""),
            "has_embedding": has_embedding,
        }
    else:
        return {
            "status": "not_enrolled"
        }
