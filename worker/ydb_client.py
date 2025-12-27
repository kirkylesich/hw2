"""YDB client module for task CRUD operations."""

import os
import ydb
from typing import Optional, Dict, Any
from datetime import datetime, timezone


class YDBClient:
    """Client for interacting with YDB database."""
    
    def __init__(self):
        """Initialize YDB client with IAM authentication."""
        self.endpoint = os.environ.get("YDB_ENDPOINT")
        self.database = os.environ.get("YDB_DATABASE")
        
        if not self.endpoint or not self.database:
            raise ValueError("YDB_ENDPOINT and YDB_DATABASE environment variables must be set")
        
        # Use MetadataUrlCredentials for service account authentication
        self.driver_config = ydb.DriverConfig(
            endpoint=self.endpoint,
            database=self.database,
            credentials=ydb.iam.MetadataUrlCredentials()
        )
        
        self.driver = ydb.Driver(self.driver_config)
        self.driver.wait(timeout=5, fail_fast=True)
        self.pool = ydb.SessionPool(self.driver)
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task by ID from YDB.
        
        Args:
            task_id: Task UUID
            
        Returns:
            Task dictionary or None if not found
        """
        def callee(session):
            query = """
                DECLARE $task_id AS Utf8;
                SELECT task_id, title, video_link, status, created_at, updated_at, error_message, pdf_key
                FROM tasks
                WHERE task_id = $task_id;
            """
            prepared_query = session.prepare(query)
            result_sets = session.transaction().execute(
                prepared_query,
                {"$task_id": task_id},
                commit_tx=True
            )
            
            for row in result_sets[0].rows:
                return {
                    "task_id": row.task_id,
                    "title": row.title,
                    "video_link": row.video_link,
                    "status": row.status,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                    "error_message": row.error_message if hasattr(row, 'error_message') else None,
                    "pdf_key": row.pdf_key if hasattr(row, 'pdf_key') else None
                }
            return None
        
        return self.pool.retry_operation_sync(callee)
    
    def update_task_status(self, task_id: str, status: str, error_message: Optional[str] = None) -> None:
        """
        Update task status in YDB.
        
        Args:
            task_id: Task UUID
            status: New status (queued, processing, completed, error)
            error_message: Optional error message for error status
        """
        def callee(session):
            updated_at = datetime.now(timezone.utc).isoformat()
            
            if error_message:
                query = """
                    DECLARE $task_id AS Utf8;
                    DECLARE $status AS Utf8;
                    DECLARE $error_message AS Utf8;
                    DECLARE $updated_at AS Utf8;
                    
                    UPDATE tasks
                    SET status = $status, error_message = $error_message, updated_at = $updated_at
                    WHERE task_id = $task_id;
                """
                prepared_query = session.prepare(query)
                session.transaction().execute(
                    prepared_query,
                    {
                        "$task_id": task_id,
                        "$status": status,
                        "$error_message": error_message,
                        "$updated_at": updated_at
                    },
                    commit_tx=True
                )
            else:
                query = """
                    DECLARE $task_id AS Utf8;
                    DECLARE $status AS Utf8;
                    DECLARE $updated_at AS Utf8;
                    
                    UPDATE tasks
                    SET status = $status, updated_at = $updated_at
                    WHERE task_id = $task_id;
                """
                prepared_query = session.prepare(query)
                session.transaction().execute(
                    prepared_query,
                    {
                        "$task_id": task_id,
                        "$status": status,
                        "$updated_at": updated_at
                    },
                    commit_tx=True
                )
        
        self.pool.retry_operation_sync(callee)
    
    def update_task_complete(self, task_id: str, pdf_key: str) -> None:
        """
        Update task as completed with PDF key.
        
        Args:
            task_id: Task UUID
            pdf_key: S3 key for the generated PDF
        """
        def callee(session):
            updated_at = datetime.now(timezone.utc).isoformat()
            
            query = """
                DECLARE $task_id AS Utf8;
                DECLARE $status AS Utf8;
                DECLARE $pdf_key AS Utf8;
                DECLARE $updated_at AS Utf8;
                
                UPDATE tasks
                SET status = $status, pdf_key = $pdf_key, updated_at = $updated_at
                WHERE task_id = $task_id;
            """
            prepared_query = session.prepare(query)
            session.transaction().execute(
                prepared_query,
                {
                    "$task_id": task_id,
                    "$status": "completed",
                    "$pdf_key": pdf_key,
                    "$updated_at": updated_at
                },
                commit_tx=True
            )
        
        self.pool.retry_operation_sync(callee)
    
    def close(self) -> None:
        """Close YDB connection."""
        if self.driver:
            self.driver.stop()
