"""
Module: media_chunk_similarity
------------------------------
Runs similarity matching between all chunked audio files and enrolled speech embeddings.
Uses Speechbrain ECAPA-voxceleb for embeddings.
Logs matches where score >= threshold.

Depends on match_logger.py for persistent match logging.
"""

import os
import numpy as np
from typing import Dict

from .match_logger import log_match
from .main import get_speechbrain_classifier
import json

# Locations
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
CHUNKED_AUDIO_DIR = os.path.join(BASE_DIR, "uploaded_voices", "chunked_audio")
ENROLLMENTS_PATH = os.path.join(BASE_DIR, "uploaded_voices", "enrollments.json")

DEFAULT_THRESHOLD = float(os.environ.get("SIMILARITY_ALERT_THRESHOLD", "0.78"))  # Customizable


def load_enrollments() -> Dict[str, dict]:
    if not os.path.exists(ENROLLMENTS_PATH):
        return {}
    with open(ENROLLMENTS_PATH, "r") as f:
        return json.load(f)


# PUBLIC_INTERFACE
def match_all_chunks_and_log(threshold: float = DEFAULT_THRESHOLD) -> int:
    """
    Runs similarity matching for all chunked audio files
    against all enrolled speaker embeddings. Logs matches above threshold.

    Args:
        threshold (float): Cosine similarity threshold (>=0.0 to 1.0)

    Returns:
        int: Number of matches logged
    """
    classifier = get_speechbrain_classifier()
    enrollments = load_enrollments()
    if not os.path.exists(CHUNKED_AUDIO_DIR):
        return 0

    # Build list of chunked audio files
    chunk_files = [
        os.path.join(CHUNKED_AUDIO_DIR, fn)
        for fn in os.listdir(CHUNKED_AUDIO_DIR)
        if fn.lower().endswith(".wav")
    ]
    if not chunk_files or not enrollments:
        return 0

    logged_matches = 0

    # Preprocess all enrollment embeddings (dict: user_id -> np.ndarray)
    prepped_enrollments = {}
    for user_id, data in enrollments.items():
        emb = np.array(data.get("embedding", []), dtype=np.float32)
        if emb.ndim == 1 and emb.size > 0:
            prepped_enrollments[user_id] = emb

    for chunk_path in chunk_files:
        # Compute chunk embedding
        try:
            signal, fs = classifier.load_audio(chunk_path)
            chunk_emb = classifier.encode_batch(signal.unsqueeze(0))
            chunk_emb_np = chunk_emb.squeeze().detach().cpu().numpy().astype(np.float32)
        except Exception:
            continue  # Ignore audio/encode errors

        # Compare to all enrollments
        for user_id, enroll_emb in prepped_enrollments.items():
            if enroll_emb.shape != chunk_emb_np.shape:
                continue
            # Cosine similarity [same logic as API]
            dot = np.dot(chunk_emb_np, enroll_emb)
            norm_chunk = np.linalg.norm(chunk_emb_np)
            norm_enroll = np.linalg.norm(enroll_emb)
            denom = (norm_chunk * norm_enroll + 1e-8)
            score = float(dot) / denom
            if score >= threshold:
                log_match(os.path.basename(chunk_path), user_id, score)
                logged_matches += 1
    return logged_matches
