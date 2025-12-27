import os
import time
import requests
from typing import Optional


def transcribe_audio(audio_s3_uri: str, folder_id: str) -> str:
    api_key = os.environ.get("YANDEX_API_KEY")
    if not api_key:
        raise ValueError("YANDEX_API_KEY environment variable is not set")
    
    recognition_url = "https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize"
    
    headers = {
        "Authorization": f"Api-Key {api_key}"
    }
    
    data = {
        "config": {
            "specification": {
                "languageCode": "ru-RU",
                "model": "general",
                "audioEncoding": "LINEAR16_PCM",  # WAV format
                "sampleRateHertz": 16000,  # 16kHz as we set in video_processor
                "audioChannelCount": 1  # Mono
            }
        },
        "audio": {
            "uri": audio_s3_uri  # Use S3 URI instead of content
        }
    }
    
    response = requests.post(recognition_url, json=data, headers=headers, timeout=30)
    response.raise_for_status()
    
    operation_id = response.json()["id"]
    
    operation_url = f"https://operation.api.cloud.yandex.net/operations/{operation_id}"
    
    max_attempts = 60  # 5 minutes with 5 second intervals
    for _ in range(max_attempts):
        time.sleep(5)
        
        response = requests.get(operation_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        operation = response.json()
        
        if operation.get("done"):
            if "error" in operation:
                raise Exception(f"Transcription failed: {operation['error']}")
            
            chunks = operation.get("response", {}).get("chunks", [])
            text_parts = []
            
            for chunk in chunks:
                alternatives = chunk.get("alternatives", [])
                if alternatives:
                    text_parts.append(alternatives[0].get("text", ""))
            
            return " ".join(text_parts)
    
    raise Exception("Transcription timeout: operation did not complete in time")
