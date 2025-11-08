"""Persistent storage for jobs using SQLite"""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import threading

from queuectl.config import get_config


class JobStorage:
    """Thread-safe job storage using SQLite"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_config("db_path")
        self._lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    command TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    next_retry_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    error_message TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_state ON jobs(state)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_next_retry ON jobs(next_retry_at)
            """)
            conn.commit()
            conn.close()
    
    def _get_connection(self):
        """Get a database connection with row factory"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_job(self, job_id: str, command: str, max_retries: int = 3) -> Dict[str, Any]:
        """Create a new job"""
        now = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            conn = self._get_connection()
            conn.execute("""
                INSERT INTO jobs (id, command, state, attempts, max_retries, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (job_id, command, "pending", 0, max_retries, now, now))
            conn.commit()
            conn.close()
        return self.get_job(job_id)
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a job by ID"""
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None
    
    def update_job(self, job_id: str, **updates) -> Optional[Dict[str, Any]]:
        """Update job fields"""
        updates["updated_at"] = datetime.utcnow().isoformat() + "Z"
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [job_id]
        
        with self._lock:
            conn = self._get_connection()
            conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)
            conn.commit()
            conn.close()
        return self.get_job(job_id)
    
    def get_pending_jobs(self, limit: int = 1) -> List[Dict[str, Any]]:
        """Get pending jobs that are ready to be processed (including failed jobs ready to retry)"""
        now = datetime.utcnow().isoformat() + "Z"
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT * FROM jobs 
            WHERE (state = 'pending' OR state = 'failed')
            AND (next_retry_at IS NULL OR next_retry_at <= ?)
            ORDER BY created_at ASC
            LIMIT ?
        """, (now, limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def acquire_job(self, job_id: str) -> bool:
        """Try to acquire a job for processing (lock it)"""
        now = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            conn = self._get_connection()
            # Acquire jobs that are pending or failed (ready to retry)
            cursor = conn.execute(
                """UPDATE jobs SET state = 'processing' 
                   WHERE id = ? 
                   AND (state = 'pending' OR state = 'failed')
                   AND (next_retry_at IS NULL OR next_retry_at <= ?)""",
                (job_id, now)
            )
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            return success
    
    def list_jobs(self, state: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List jobs optionally filtered by state"""
        conn = self._get_connection()
        if state:
            cursor = conn.execute(
                "SELECT * FROM jobs WHERE state = ? ORDER BY created_at DESC LIMIT ?",
                (state, limit)
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_dlq_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs in Dead Letter Queue"""
        return self.list_jobs(state="dead")
    
    def get_stats(self) -> Dict[str, int]:
        """Get job statistics"""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT state, COUNT(*) as count 
            FROM jobs 
            GROUP BY state
        """)
        stats = {row["state"]: row["count"] for row in cursor.fetchall()}
        conn.close()
        return stats
    
    def reset_job_for_retry(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Reset a DLQ job for retry"""
        with self._lock:
            conn = self._get_connection()
            conn.execute("""
                UPDATE jobs 
                SET state = 'pending', 
                    attempts = 0, 
                    next_retry_at = NULL,
                    error_message = NULL,
                    updated_at = ?
                WHERE id = ? AND state = 'dead'
            """, (datetime.utcnow().isoformat() + "Z", job_id))
            conn.commit()
            conn.close()
        return self.get_job(job_id)

