import os
import requests
import ffmpeg
from typing import Tuple


def download_video(video_url: str, output_path: str) -> None:
    response = requests.get(video_url, stream=True, timeout=300)
    response.raise_for_status()
    
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)


def extract_audio(video_path: str, audio_path: str) -> None:
    try:
        stream = ffmpeg.input(video_path)
        stream = ffmpeg.output(
            stream,
            audio_path,
            acodec='pcm_s16le',
            ar='16000',
            ac='1',
            vn=None,
            **{'threads': '0'}
        )
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as e:
        error_message = e.stderr.decode() if e.stderr else str(e)
        raise Exception(f"Audio extraction failed: {error_message}")


def get_temp_paths(task_id: str) -> Tuple[str, str]:
    video_path = f"/tmp/{task_id}_video.mp4"
    audio_path = f"/tmp/{task_id}_audio.wav"
    return video_path, audio_path


def cleanup_temp_files(task_id: str) -> None:
    video_path, audio_path = get_temp_paths(task_id)
    
    if os.path.exists(video_path):
        os.remove(video_path)
    
    if os.path.exists(audio_path):
        os.remove(audio_path)
