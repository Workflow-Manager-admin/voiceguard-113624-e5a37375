"""
Module: match_logger
--------------------
Handles logging of audio chunk matches exceeding the similarity threshold.

Log entries are stored in a JSON lines file for efficient retrieval.

Each log record contains:
- chunk_filename: The chunked audio file checked
- matched_user_id: The enrolled user ID that matched
- score: Cosine similarity score
- timestamp: When the match occurred (ISO 8601)
"""

import os
import json
import datetime

LOG_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../uploaded_voices/match_log.jsonl")
)

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


# PUBLIC_INTERFACE
def log_match(chunk_filename: str, matched_user_id: str, score: float):
    """Append a match record to the match log.

    Args:
        chunk_filename (str): Filename or ref of matched audio chunk
        matched_user_id (str): User ID that matched
        score (float): Similarity score
    """
    entry = {
        "chunk_filename": chunk_filename,
        "matched_user_id": matched_user_id,
        "score": score,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


# PUBLIC_INTERFACE
def get_logged_matches():
    """Retrieve all logged matches as a list of dicts (most recent last)."""
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as f:
        return [json.loads(line) for line in f if line.strip()]
