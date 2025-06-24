from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import status
from fastapi import BackgroundTasks

import os
import json
import numpy as np
from typing import Dict

# Media crawling
try:
    from .media_crawler import crawl_youtube_and_download_audio, load_status
except ImportError:
    # Local dev fallback if running as script
    from media_crawler import crawl_youtube_and_download_audio, load_status

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
        {"name": "voice", "description": "User voice upload and enrollment API"},
        {"name": "test", "description": "Voice test and similarity scoring"},
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

# PUBLIC_INTERFACE


@app.post(
    "/crawl/youtube",
    tags=["media", "crawl"],
    summary="Trigger YouTube media crawl and audio extraction",
    description=(
        "Triggers crawling of a YouTube channel, playlist, or video URL. "
        "Downloads newest audio and returns summary."
    ),
    response_description="Crawling job result summary as JSON.",
)
async def trigger_youtube_crawl(
    background_tasks: BackgroundTasks,
    youtube_url: str = Query(
        ..., description="YouTube channel/playlist/video URL"
    ),
    max_videos: int = Query(
        3,
        ge=1,
        le=10,
        description="Number of latest videos to crawl/download",
    ),
):
    """
    PUBLIC_INTERFACE

    Initiate a crawl of YouTube media, downloading audio WAVs for up to `max_videos` videos.
    Operation may take time; runs in background and status can be polled via /crawl/status.

    Args:
        youtube_url (str): YouTube channel/playlist/video url to crawl.
        max_videos (int): Max number of latest videos to download.

    Returns:
        JSON: Job initiation status and preliminary summary.
    """

    def run_crawl():
        crawl_youtube_and_download_audio(youtube_url, max_videos=max_videos)

    background_tasks.add_task(run_crawl)
    return {
        "status": "started",
        "detail": (
            f"Crawling {youtube_url} for up to {max_videos} videos. "
            "Check /crawl/status."
        ),
    }


# PUBLIC_INTERFACE
@app.get(
    "/crawl/status",
    tags=["media", "crawl"],
    summary="Check latest media crawl status",
    description="Returns status of the most recent crawl job (YouTube, etc.).",
    response_description="Status info, download results, or error.",
)
def get_latest_crawl_status():
    """
    PUBLIC_INTERFACE

    Get the status/result of the last media crawling and audio extraction job.

    Returns:
        JSON: status for the most recent crawl, with files, timestamps, etc.
    """
    status_data = load_status()
    if not status_data:
        return {
            "status": "no_recent_crawl",
            "detail": (
                "No crawl has been performed yet in this backend instance."
            ),
        }
    return status_data


@app.post(
    "/test/voice",
    tags=["test"],
    summary="Test an uploaded audio sample against all enrolled voices",
    description=(
        "Upload a voice/audio sample. The embedding is computed (Speechbrain ECAPA-voxceleb) "
        "and compared to all enrolled embeddings. Returns a ranked list of matches (user IDs and similarity scores)."
    ),
    response_description="A ranked list of enrolled user IDs and their similarity scores, best match first.",
)
async def test_voice(
    file: UploadFile = File(..., description="Audio file for test (wav, mp3, etc.)"),
):
    """
    PUBLIC_INTERFACE

    Test an uploaded audio sample by computing its embedding and comparing to all
    enrolled voice embeddings, returning a ranked list of matches.

    - Accepts: WAV, MP3, M4A, OPUS, OGG files.
    - Returns: List of dicts with user_id and similarity_score,
      ranked best match first.

    Args:
        file (UploadFile): Audio file.

    Returns:
        JSON: {
            "matches": [{"user_id":..., "score":...}, ...],
            "num_enrollments": int
        }
    """
    # Validate and save the uploaded file temporarily
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".wav", ".mp3", ".m4a", ".opus", ".ogg"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    tmp_path = os.path.join(UPLOAD_DIR, f"_test_{file.filename}")
    try:
        with open(tmp_path, "wb") as out_file:
            while chunk := await file.read(8192):
                out_file.write(chunk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed saving file: {str(e)}")

    # Compute test sample embedding
    try:
        test_embedding = compute_embedding(tmp_path)
    except Exception as e:
        os.remove(tmp_path)
        raise HTTPException(
            status_code=500,
            detail=f"Embedding computation failed: {str(e)}"
        )
    # Remove temp file
    try:
        os.remove(tmp_path)
    except Exception:
        pass

    # Prepare numpy array for test embedding
    test_vec = np.array(test_embedding, dtype=np.float32)

    # Load all enrollments
    enrollments = load_enrollments()
    matches = []
    for user_id, data in enrollments.items():
        enroll_emb = np.array(data.get("embedding", []), dtype=np.float32)
        # Defensive: skip if shape mismatch or invalid embedding
        if enroll_emb.shape != test_vec.shape or len(enroll_emb.shape) != 1:
            continue
        # Cosine similarity
        dot = np.dot(test_vec, enroll_emb)
        norm_test = np.linalg.norm(test_vec)
        norm_enroll = np.linalg.norm(enroll_emb)
        denom = (norm_test * norm_enroll + 1e-8)
        score = float(dot) / denom
        matches.append({"user_id": user_id, "score": score})

    # Rank by descending similarity
    matches_sorted = sorted(matches, key=lambda x: x["score"], reverse=True)
    return JSONResponse(
        content={
            "matches": matches_sorted,
            "num_enrollments": len(enrollments),
            "detail": (
                "Tested against all enrolled voices. "
                "Higher score = closer match."
            ),
        },
        status_code=status.HTTP_200_OK,
    )


# PUBLIC_INTERFACE

# PUBLIC_INTERFACE


@app.post(
    "/crawl/youtube",
    tags=["media", "crawl"],
    summary="Trigger YouTube media crawl and audio extraction",
    description=(
        "Triggers crawling of a YouTube channel, playlist, or video URL. "
        "Downloads newest audio and returns summary."
    ),
    response_description="Crawling job result summary as JSON.",
)
async def trigger_youtube_crawl(
    background_tasks: BackgroundTasks,
    youtube_url: str = Query(
        ..., description="YouTube channel/playlist/video URL"
    ),
    max_videos: int = Query(
        3,
        ge=1,
        le=10,
        description="Number of latest videos to crawl/download",
    ),
):
    """
    PUBLIC_INTERFACE

    Initiate a crawl of YouTube media, downloading audio WAVs for up to `max_videos` videos.
    Operation may take time; runs in background and status can be polled via /crawl/status.

    Args:
        youtube_url (str): YouTube channel/playlist/video url to crawl.
        max_videos (int): Max number of latest videos to download.

    Returns:
        JSON: Job initiation status and preliminary summary.
    """

    def run_crawl():
        crawl_youtube_and_download_audio(youtube_url, max_videos=max_videos)

    background_tasks.add_task(run_crawl)
    return {
        "status": "started",
        "detail": (
            f"Crawling {youtube_url} for up to {max_videos} videos. "
            "Check /crawl/status."
        ),
    }


# PUBLIC_INTERFACE
@app.get(
    "/crawl/status",
    tags=["media", "crawl"],
    summary="Check latest media crawl status",
    description="Returns status of the most recent crawl job (YouTube, etc.).",
    response_description="Status info, download results, or error.",
)
def get_latest_crawl_status():
    """
    PUBLIC_INTERFACE

    Get the status/result of the last media crawling and audio extraction job.

    Returns:
        JSON: status for the most recent crawl, with files, timestamps, etc.
    """
    status_data = load_status()
    if not status_data:
        return {
            "status": "no_recent_crawl",
            "detail": (
                "No crawl has been performed yet in this backend instance."
            ),
        }
    return status_data
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
