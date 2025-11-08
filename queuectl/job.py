"""Job model and execution logic"""

import subprocess
import signal
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from queuectl.config import get_config


class Job:
    """Represents a job in the queue"""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data["id"]
        self.command = data["command"]
        self.state = data["state"]
        self.attempts = data["attempts"]
        self.max_retries = data["max_retries"]
        self.next_retry_at = data.get("next_retry_at")
        self.created_at = data["created_at"]
        self.updated_at = data["updated_at"]
        self.completed_at = data.get("completed_at")
        self.error_message = data.get("error_message")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary"""
        return {
            "id": self.id,
            "command": self.command,
            "state": self.state,
            "attempts": self.attempts,
            "max_retries": self.max_retries,
            "next_retry_at": self.next_retry_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message,
        }
    
    def execute(self, timeout: Optional[int] = None):
        """
        Execute the job command
        Returns: (success, error_message)
        """
        try:
            # Determine shell based on OS
            shell = os.name == 'nt'  # Windows uses cmd, Unix uses /bin/sh
            
            if timeout:
                result = subprocess.run(
                    self.command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False
                )
            else:
                result = subprocess.run(
                    self.command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=False
                )
            
            if result.returncode == 0:
                return True, None
            else:
                error_msg = result.stderr or result.stdout or f"Command failed with exit code {result.returncode}"
                return False, error_msg
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout} seconds"
        except FileNotFoundError:
            return False, f"Command not found: {self.command}"
        except Exception as e:
            return False, str(e)
    
    def calculate_next_retry(self) -> str:
        """Calculate next retry time using exponential backoff"""
        backoff_base = get_config("backoff_base", 2)
        delay_seconds = backoff_base ** self.attempts
        next_retry = datetime.utcnow() + timedelta(seconds=delay_seconds)
        return next_retry.isoformat() + "Z"
    
    def should_retry(self) -> bool:
        """Check if job should be retried"""
        return self.attempts < self.max_retries
    
    def mark_for_retry(self) -> Dict[str, Any]:
        """Prepare job for retry with exponential backoff"""
        self.attempts += 1
        if self.should_retry():
            self.state = "failed"
            self.next_retry_at = self.calculate_next_retry()
        else:
            self.state = "dead"
            self.next_retry_at = None
        return self.to_dict()
    
    def mark_completed(self) -> Dict[str, Any]:
        """Mark job as completed"""
        self.state = "completed"
        self.completed_at = datetime.utcnow().isoformat() + "Z"
        return self.to_dict()
    
    def mark_failed(self, error_message: str) -> Dict[str, Any]:
        """Mark job as failed"""
        self.error_message = error_message
        return self.mark_for_retry()

