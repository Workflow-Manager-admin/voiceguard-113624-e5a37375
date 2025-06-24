import os
from typing import Dict, Optional
import datetime

CRAWL_STATUS_FILE = os.path.join(
    os.path.dirname(__file__), "../../crawl_status.json"
)
CRAWL_AUDIO_DIR = os.path.join(
    os.path.dirname(__file__), "../../uploaded_voices/crawled_audio"
)

os.makedirs(CRAWL_AUDIO_DIR, exist_ok=True)


def write_status(status: Dict):
    """Save the latest crawl status to a JSON file."""
    import json
    with open(CRAWL_STATUS_FILE, "w") as f:
        json.dump(status, f)


def load_status() -> Optional[Dict]:
    """Load the latest crawl status from file."""
    import json
    if not os.path.exists(CRAWL_STATUS_FILE):
        return None
    try:
        with open(CRAWL_STATUS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None


# PUBLIC_INTERFACE
def crawl_youtube_and_download_audio(
    youtube_url: str, max_videos: int = 3
) -> Dict:
    """
    Crawls a YouTube URL (channel or playlist or video), downloads latest audio(s)
    and chunks each audio file into fixed-duration segments suitable for downstream
    similarity processing.

    Args:
        youtube_url (str): YouTube URL to crawl.
        max_videos (int): How many latest videos to process.

    Returns:
        dict: status information including downloaded and chunked files.
    """
    import yt_dlp

    # Import chunking inline to avoid cyclic or cold import issues
    try:
        from .audio_chunking import chunk_wav_audio_file
    except ImportError:
        from audio_chunking import chunk_wav_audio_file

    timestamp = datetime.datetime.now().isoformat()
    status = {
        "start_time": timestamp,
        "platform": "YouTube",
        "target_url": youtube_url,
        "success": False,
        "downloaded_files": [],
        "audio_chunks": {},
        "error": None,
    }

    # yt-dlp options
    ydl_opts = {
        "quiet": True,
        "format": "bestaudio/best",
        "outtmpl": os.path.join(CRAWL_AUDIO_DIR, "%(id)s.%(ext)s"),
        "max_downloads": max_videos,
        "noplaylist": False,
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "wav"},
        ],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(youtube_url, download=True)
            if "entries" in result:
                entries = result["entries"][:max_videos]
            else:
                entries = [result]
            files = []
            audio_chunks = {}
            for entry in entries:
                base_id = entry.get("id")
                ext = "wav"
                save_path = os.path.abspath(
                    os.path.join(CRAWL_AUDIO_DIR, f"{base_id}.{ext}")
                )
                if os.path.exists(save_path):
                    files.append(
                        {
                            "video_id": base_id,
                            "title": entry.get("title"),
                            "filepath": save_path,
                        }
                    )
                    try:
                        # Automatically chunk the newly downloaded audio
                        chunk_files = chunk_wav_audio_file(save_path)
                        audio_chunks[base_id] = chunk_files
                    except Exception as ex:
                        audio_chunks[base_id] = {"error": str(ex)}
            status["downloaded_files"] = files
            status["audio_chunks"] = audio_chunks
            status["success"] = True
    except Exception as ex:
        status["error"] = str(ex)
        status["success"] = False

    write_status(status)
    return status

# Stub functions for TikTok/Instagram/general web if needed in future.
