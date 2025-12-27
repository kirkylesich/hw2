import os
import logging
from typing import Dict, Any
from ydb_client import YDBClient
from storage_client import StorageClient
from video_processor import download_video, extract_audio, get_temp_paths, cleanup_temp_files
from transcription import transcribe_audio
from summary import generate_summary
from pdf_generator import generate_pdf

logger = logging.getLogger(__name__)


def validate_yandex_disk_link(video_link: str) -> Dict[str, Any]:
    import requests
    
    api_url = "https://cloud-api.yandex.net/v1/disk/public/resources"
    params = {"public_key": video_link}
    
    response = requests.get(api_url, params=params, timeout=10)
    
    if response.status_code != 200:
        raise Exception("Invalid or inaccessible video link")
    
    metadata = response.json()
    
    mime_type = metadata.get("mime_type", "")
    if not mime_type.startswith("video/"):
        raise Exception(f"File is not a video (mime_type: {mime_type})")
    
    file_size = metadata.get("size", 0)
    max_size = 200 * 1024 * 1024  # 200 MB
    
    if file_size > max_size:
        size_mb = file_size / (1024 * 1024)
        raise Exception(f"Video file is too large ({size_mb:.1f} MB). Maximum supported size is 200 MB due to serverless container limitations. Please use a smaller video file.")
    
    return metadata


def get_download_url(video_link: str) -> str:
    import requests
    
    api_url = "https://cloud-api.yandex.net/v1/disk/public/resources/download"
    params = {"public_key": video_link}
    
    response = requests.get(api_url, params=params, timeout=10)
    response.raise_for_status()
    
    return response.json()["href"]


def process_task(task_id: str) -> None:
    ydb_client = YDBClient()
    storage_client = StorageClient()
    folder_id = os.environ.get("FOLDER_ID")
    
    if not folder_id:
        raise ValueError("FOLDER_ID environment variable must be set")
    
    try:
        task = ydb_client.get_task(task_id)
        if not task:
            raise Exception(f"Task {task_id} not found")
        
        logger.info(f"Processing task {task_id}: {task['title']}")
        
        if task["status"] in ["completed", "error"]:
            logger.info(f"Task {task_id} already in final state: {task['status']}")
            return
        
        ydb_client.update_task_status(task_id, "processing")
        logger.info(f"Task {task_id} status updated to processing")
        
        logger.info(f"Validating video link for task {task_id}")
        try:
            metadata = validate_yandex_disk_link(task["video_link"])
            logger.info(f"Video link validated: {metadata.get('name')}")
        except Exception as e:
            error_msg = f"Video link validation failed: {str(e)}"
            logger.error(error_msg)
            ydb_client.update_task_status(task_id, "error", error_msg)
            return
        
        logger.info(f"Downloading video for task {task_id}")
        video_path, audio_path = get_temp_paths(task_id)
        
        try:
            download_url = get_download_url(task["video_link"])
            download_video(download_url, video_path)
            logger.info(f"Video downloaded to {video_path}")
            
        except Exception as e:
            error_msg = f"Video download failed: {str(e)}"
            logger.error(error_msg)
            cleanup_temp_files(task_id)
            ydb_client.update_task_status(task_id, "error", error_msg)
            return
        
        logger.info(f"Extracting audio for task {task_id}")
        try:
            extract_audio(video_path, audio_path)
            logger.info(f"Audio extracted to {audio_path}")
            
            if os.path.exists(video_path):
                os.remove(video_path)
                logger.info(f"Video file deleted to free up space: {video_path}")
            
            audio_s3_key = f"temp/{task_id}/audio.wav"
            storage_client.upload_file(audio_path, audio_s3_key)
            logger.info(f"Audio uploaded to S3: {audio_s3_key}")
            
            bucket_name = os.environ.get("S3_BUCKET") or os.environ.get("BUCKET_NAME")
            audio_s3_uri = f"https://storage.yandexcloud.net/{bucket_name}/{audio_s3_key}"
            logger.info(f"Audio S3 URI: {audio_s3_uri}")
        except Exception as e:
            error_msg = f"Audio extraction failed: {str(e)}"
            logger.error(error_msg)
            cleanup_temp_files(task_id)
            ydb_client.update_task_status(task_id, "error", error_msg)
            return
        
        logger.info(f"Transcribing audio for task {task_id}")
        try:
            transcribed_text = transcribe_audio(audio_s3_uri, folder_id)
            logger.info(f"Audio transcribed, length: {len(transcribed_text)} characters")
        except Exception as e:
            error_msg = f"Transcription failed: {str(e)}"
            logger.error(error_msg)
            cleanup_temp_files(task_id)
            ydb_client.update_task_status(task_id, "error", error_msg)
            return
        
        logger.info(f"Generating summary for task {task_id}")
        try:
            summary_text = generate_summary(transcribed_text, folder_id)
            logger.info(f"Summary generated, length: {len(summary_text)} characters")
        except Exception as e:
            error_msg = f"Summary generation failed: {str(e)}"
            logger.error(error_msg)
            cleanup_temp_files(task_id)
            ydb_client.update_task_status(task_id, "error", error_msg)
            return
        
        logger.info(f"Generating PDF for task {task_id}")
        pdf_path = f"/tmp/{task_id}.pdf"
        try:
            generate_pdf(task["title"], summary_text, pdf_path)
            logger.info(f"PDF generated at {pdf_path}")
        except Exception as e:
            error_msg = f"PDF generation failed: {str(e)}"
            logger.error(error_msg)
            cleanup_temp_files(task_id)
            ydb_client.update_task_status(task_id, "error", error_msg)
            return
        
        logger.info(f"Uploading PDF for task {task_id}")
        pdf_key = f"pdfs/{task_id}.pdf"
        try:
            storage_client.upload_file(pdf_path, pdf_key)
            logger.info(f"PDF uploaded to S3: {pdf_key}")
            
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception as e:
            error_msg = f"PDF upload failed: {str(e)}"
            logger.error(error_msg)
            cleanup_temp_files(task_id)
            ydb_client.update_task_status(task_id, "error", error_msg)
            return
        
        logger.info(f"Marking task {task_id} as completed")
        ydb_client.update_task_complete(task_id, pdf_key)
        
        cleanup_temp_files(task_id)
        
        logger.info(f"Task {task_id} completed successfully")
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        cleanup_temp_files(task_id)
        ydb_client.update_task_status(task_id, "error", error_msg)
    finally:
        ydb_client.close()
