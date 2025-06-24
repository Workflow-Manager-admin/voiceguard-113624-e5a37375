"""
Audio chunking utility.

Splits WAV audio files in crawled_audio/ into chunks of fixed duration (e.g. 10 or 30 seconds)
and saves the result to chunk files for downstream similarity matching.
"""

import os
from typing import List
import torchaudio


CHUNK_SECONDS = 10  # You can adjust to e.g. 30 for longer chunks
CRAWLED_AUDIO_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../uploaded_voices/crawled_audio")
)
CHUNKED_AUDIO_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../uploaded_voices/chunked_audio")
)

os.makedirs(CHUNKED_AUDIO_DIR, exist_ok=True)


# PUBLIC_INTERFACE
def chunk_wav_audio_file(input_wav_path: str, chunk_sec: int = CHUNK_SECONDS) -> List[str]:
    """
    Splits an input WAV file into fixed-duration audio chunks and saves them.

    Args:
        input_wav_path (str): Path to source WAV file.
        chunk_sec (int): Duration (seconds) per chunk.

    Returns:
        List[str]: List of chunk file paths produced.
    """
    if not os.path.exists(input_wav_path):
        raise FileNotFoundError(f"Audio file not found: {input_wav_path}")
    if os.path.splitext(input_wav_path)[1].lower() != ".wav":
        raise ValueError(f"Input file must be a WAV file: {input_wav_path}")

    # Load audio using torchaudio for robust handling
    waveform, sample_rate = torchaudio.load(input_wav_path)
    duration = waveform.shape[1] / sample_rate

    num_chunks = int(duration // chunk_sec) + (1 if (duration % chunk_sec) else 0)
    chunk_paths = []
    base_name = os.path.splitext(os.path.basename(input_wav_path))[0]

    for i in range(num_chunks):
        start_sample = int(i * chunk_sec * sample_rate)
        end_sample = int(
            min((i + 1) * chunk_sec * sample_rate, waveform.shape[1])
        )
        chunk_waveform = waveform[:, start_sample:end_sample]
        if chunk_waveform.shape[1] == 0:
            continue

        chunk_fn = f"{base_name}_chunk{i + 1:03d}_{chunk_sec}s.wav"
        chunk_path = os.path.join(CHUNKED_AUDIO_DIR, chunk_fn)

        torchaudio.save(chunk_path, chunk_waveform, sample_rate)
        chunk_paths.append(chunk_path)

    return chunk_paths


# PUBLIC_INTERFACE
def chunk_all_crawled_audio(chunk_sec: int = CHUNK_SECONDS) -> dict:
    """
    Processes all WAV files in the crawled_audio/ directory. Each is split
    into chunks under chunked_audio/.

    Args:
        chunk_sec (int): The target chunk duration (seconds).

    Returns:
        dict: Mapping from source filename to list of chunk files produced.
    """
    if not os.path.exists(CRAWLED_AUDIO_DIR):
        raise FileNotFoundError("Crawled audio directory does not exist.")

    chunked = {}
    for filename in sorted(os.listdir(CRAWLED_AUDIO_DIR)):
        if not filename.lower().endswith(".wav"):
            continue
        src_path = os.path.join(CRAWLED_AUDIO_DIR, filename)
        try:
            chunk_files = chunk_wav_audio_file(src_path, chunk_sec=chunk_sec)
        except Exception as e:
            chunked[filename] = {"error": str(e)}
            continue
        chunked[filename] = chunk_files
    return chunked
