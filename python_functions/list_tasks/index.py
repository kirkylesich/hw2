"""
Cloud Function: List Tasks
Handles GET /tasks requests (JSON API)
"""
import json
import os
from datetime import datetime, timedelta
import ydb
import ydb.iam
import boto3


def handler(event, context):
    """
    Main handler for Cloud Function
    
    Args:
        event: Request event from API Gateway
        context: Function execution context
        
    Returns:
        dict: HTTP response with status code, headers, and body
    """
    try:
        # Get environment variables
        ydb_endpoint = os.environ['YDB_ENDPOINT']
        ydb_database = os.environ['YDB_DATABASE']
        s3_bucket = os.environ['S3_BUCKET']
        
        # Initialize YDB driver
        driver = ydb.Driver(
            endpoint=ydb_endpoint,
            database=ydb_database,
            credentials=ydb.iam.MetadataUrlCredentials(),
        )
        driver.wait(fail_fast=True, timeout=5)
        pool = ydb.SessionPool(driver)
        
        # Query all tasks from YDB, sorted by created_at DESC
        tasks = []
        
        def query_tasks(session):
            result_sets = session.transaction().execute(
                """
                SELECT task_id, title, video_link, status, created_at, updated_at, error_message, pdf_key
                FROM tasks
                ORDER BY created_at DESC;
                """,
                commit_tx=True,
            )
            return result_sets[0].rows
        
        rows = pool.retry_operation_sync(query_tasks)
        
        # Initialize S3 client for presigned URLs
        s3 = boto3.client(
            's3',
            endpoint_url=os.environ.get('S3_ENDPOINT', 'https://storage.yandexcloud.net'),
            region_name=os.environ.get('AWS_REGION', 'ru-central1'),
        )
        
        # Process each task
        for row in rows:
            task = {
                'task_id': row.task_id.decode('utf-8') if isinstance(row.task_id, bytes) else row.task_id,
                'title': row.title.decode('utf-8') if isinstance(row.title, bytes) else row.title,
                'video_link': row.video_link.decode('utf-8') if isinstance(row.video_link, bytes) else row.video_link,
                'status': row.status.decode('utf-8') if isinstance(row.status, bytes) else row.status,
                'created_at': row.created_at.decode('utf-8') if isinstance(row.created_at, bytes) else row.created_at,
            }
            
            # Add error message if present
            if row.error_message:
                task['error_message'] = row.error_message.decode('utf-8') if isinstance(row.error_message, bytes) else row.error_message
            
            # Generate presigned URL for completed tasks
            if task['status'] == 'completed' and row.pdf_key:
                pdf_key = row.pdf_key.decode('utf-8') if isinstance(row.pdf_key, bytes) else row.pdf_key
                try:
                    pdf_url = s3.generate_presigned_url(
                        'get_object',
                        Params={
                            'Bucket': s3_bucket,
                            'Key': pdf_key,
                        },
                        ExpiresIn=3600,  # 1 hour
                    )
                    task['pdf_url'] = pdf_url
                except Exception as e:
                    print(f"Failed to generate presigned URL for {pdf_key}: {e}")
            
            tasks.append(task)
        
        # Close driver
        driver.stop()
        
        # Return JSON response
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'tasks': tasks}),
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Internal server error: {str(e)}'}),
        }
