import os
import boto3
from typing import BinaryIO


class StorageClient:
    def __init__(self):
        self.bucket = os.environ.get("S3_BUCKET") or os.environ.get("BUCKET_NAME")
        self.endpoint = os.environ.get("S3_ENDPOINT", "https://storage.yandexcloud.net")
        
        if not self.bucket:
            raise ValueError("S3_BUCKET or BUCKET_NAME environment variable must be set")
        
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name=os.environ.get("AWS_REGION", "ru-central1")
        )
    
    def upload_file(self, file_path: str, s3_key: str) -> None:
        self.s3_client.upload_file(file_path, self.bucket, s3_key)
    
    def download_file(self, s3_key: str, file_path: str) -> None:
        self.s3_client.download_file(self.bucket, s3_key, file_path)
    
    def upload_fileobj(self, file_obj: BinaryIO, s3_key: str) -> None:
        self.s3_client.upload_fileobj(file_obj, self.bucket, s3_key)
