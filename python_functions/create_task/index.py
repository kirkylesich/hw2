"""
Cloud Function: Create Task
Handles POST /tasks requests
"""
import json
import os
import uuid
from datetime import datetime, timezone
import ydb
import ydb.iam
import boto3


def ensure_table_exists(pool):
    """
    Ensure the tasks table exists in YDB.
    Creates it if it doesn't exist.
    """
    def create_table(session):
        session.execute_scheme("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id Utf8,
                title Utf8,
                video_link Utf8,
                status Utf8,
                created_at Utf8,
                updated_at Utf8,
                error_message Utf8,
                pdf_key Utf8,
                PRIMARY KEY (task_id)
            );
        """)
    
    try:
        pool.retry_operation_sync(create_table)
    except Exception as e:
        # Table might already exist, that's okay
        print(f"Table creation note: {e}")


def validate_non_empty(value: str, field_name: str) -> None:
    """Validate that a string is not empty or whitespace-only"""
    if not value or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")


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
        # Parse request body - handle both JSON and form-urlencoded
        body = event.get('body', '')
        is_base64 = event.get('isBase64Encoded', False)
        
        # Decode base64 if needed
        if is_base64 and isinstance(body, str):
            import base64
            body = base64.b64decode(body).decode('utf-8')
        
        headers = event.get('headers', {})
        
        # Normalize header keys to lowercase
        headers_lower = {k.lower(): v for k, v in headers.items()}
        content_type = headers_lower.get('content-type', '')
        
        if 'application/x-www-form-urlencoded' in content_type or not content_type:
            # Parse form data
            from urllib.parse import parse_qs
            if isinstance(body, str) and body:
                parsed = parse_qs(body)
                title = parsed.get('title', [''])[0]
                video_link = parsed.get('video_link', [''])[0]
            else:
                title = ''
                video_link = ''
        else:
            # Parse JSON
            if isinstance(body, str) and body:
                try:
                    request_data = json.loads(body)
                except json.JSONDecodeError:
                    request_data = {}
            else:
                request_data = body if body else {}
            
            title = request_data.get('title', '')
            video_link = request_data.get('video_link', '')
        
        # Validate input
        validate_non_empty(title, 'title')
        validate_non_empty(video_link, 'video_link')
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        # Get environment variables
        ydb_endpoint = os.environ['YDB_ENDPOINT']
        ydb_database = os.environ['YDB_DATABASE']
        queue_url = os.environ['MQ_QUEUE_URL']
        
        # Initialize YDB driver
        driver = ydb.Driver(
            endpoint=ydb_endpoint,
            database=ydb_database,
            credentials=ydb.iam.MetadataUrlCredentials(),
        )
        driver.wait(fail_fast=True, timeout=5)
        pool = ydb.SessionPool(driver)
        
        # Ensure table exists (idempotent operation)
        ensure_table_exists(pool)
        
        # Insert task into YDB
        def insert_task(session):
            prepared_query = session.prepare(
                """
                DECLARE $task_id AS Utf8;
                DECLARE $title AS Utf8;
                DECLARE $video_link AS Utf8;
                DECLARE $status AS Utf8;
                DECLARE $created_at AS Utf8;
                DECLARE $updated_at AS Utf8;
                
                UPSERT INTO tasks (task_id, title, video_link, status, created_at, updated_at)
                VALUES ($task_id, $title, $video_link, $status, $created_at, $updated_at);
                """
            )
            session.transaction(ydb.SerializableReadWrite()).execute(
                prepared_query,
                {
                    '$task_id': task_id,
                    '$title': title,
                    '$video_link': video_link,
                    '$status': 'queued',
                    '$created_at': now,
                    '$updated_at': now,
                },
                commit_tx=True,
            )
        
        pool.retry_operation_sync(insert_task)
        
        # Send message to Message Queue
        sqs = boto3.client(
            'sqs',
            endpoint_url=os.environ.get('MQ_ENDPOINT', 'https://message-queue.api.cloud.yandex.net'),
            region_name=os.environ.get('AWS_REGION', 'ru-central1'),
        )
        
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({'task_id': task_id}),
        )
        
        # Close driver
        driver.stop()
        
        # Return redirect to /tasks
        return {
            'statusCode': 302,
            'headers': {
                'Location': '/tasks',
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'task_id': task_id,
                'status': 'queued',
            }),
        }
        
    except ValueError as e:
        # Validation error
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)}),
        }
    except Exception as e:
        # Infrastructure error
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Internal server error: {str(e)}'}),
        }
