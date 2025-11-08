"""Worker process management"""

import os
import sys
import time
import signal
import multiprocessing
from pathlib import Path
from typing import Optional
import json

from queuectl.storage import JobStorage
from queuectl.job import Job
from queuectl.config import get_config, CONFIG_DIR


class WorkerManager:
    """Manages worker processes"""
    
    def __init__(self):
        self.pid_file = Path(get_config("worker_pid_file"))
        self.workers: list[multiprocessing.Process] = []
        self.running = False
    
    def _worker_process(self, worker_id: int):
        """Main worker process loop"""
        storage = JobStorage()
        print(f"Worker {worker_id} started (PID: {os.getpid()})", file=sys.stderr)
        
        def signal_handler(sig, frame):
            print(f"Worker {worker_id} received shutdown signal", file=sys.stderr)
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        while True:
            try:
                # Get pending jobs
                pending_jobs = storage.get_pending_jobs(limit=1)
                
                if not pending_jobs:
                    time.sleep(1)  # No jobs, wait a bit
                    continue
                
                job_data = pending_jobs[0]
                job_id = job_data["id"]
                
                # Try to acquire the job
                if not storage.acquire_job(job_id):
                    time.sleep(0.5)  # Job already taken, try again
                    continue
                
                # Process the job
                job = Job(job_data)
                success, error_msg = job.execute()
                
                if success:
                    job.mark_completed()
                    storage.update_job(job_id, **job.to_dict())
                    print(f"Worker {worker_id}: Job {job_id} completed", file=sys.stderr)
                else:
                    job.mark_failed(error_msg)
                    storage.update_job(job_id, **job.to_dict())
                    
                    if job.state == "dead":
                        print(f"Worker {worker_id}: Job {job_id} moved to DLQ after {job.attempts} attempts", file=sys.stderr)
                    else:
                        print(f"Worker {worker_id}: Job {job_id} failed, will retry (attempt {job.attempts}/{job.max_retries})", file=sys.stderr)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Worker {worker_id} error: {e}", file=sys.stderr)
                time.sleep(1)
    
    def start_workers(self, count: int = 1):
        """Start worker processes"""
        if self.running:
            print("Workers are already running", file=sys.stderr)
            return
        
        self.running = True
        self.workers = []
        
        for i in range(count):
            process = multiprocessing.Process(
                target=self._worker_process,
                args=(i + 1,),
                daemon=False
            )
            process.start()
            self.workers.append(process)
        
        # Save worker PIDs
        pids = [p.pid for p in self.workers]
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pid_file, "w") as f:
            json.dump({"pids": pids, "count": count}, f)
        
        print(f"Started {count} worker(s)", file=sys.stderr)
        for i, worker in enumerate(self.workers):
            print(f"  Worker {i+1}: PID {worker.pid}", file=sys.stderr)
    
    def stop_workers(self):
        """Stop all worker processes gracefully"""
        if not self.pid_file.exists():
            print("No workers are running", file=sys.stderr)
            return
        
        try:
            with open(self.pid_file, "r") as f:
                data = json.load(f)
                pids = data.get("pids", [])
            
            if not pids:
                print("No worker PIDs found", file=sys.stderr)
                return
            
            print(f"Stopping {len(pids)} worker(s)...", file=sys.stderr)
            
            # Send SIGTERM to all workers
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGTERM)
                    print(f"Sent termination signal to PID {pid}", file=sys.stderr)
                except ProcessLookupError:
                    print(f"PID {pid} not found (already stopped)", file=sys.stderr)
                except Exception as e:
                    print(f"Error stopping PID {pid}: {e}", file=sys.stderr)
            
            # Wait for processes to finish (with timeout)
            import time
            timeout = 10
            start_time = time.time()
            
            for pid in pids[:]:  # Copy list
                try:
                    while True:
                        os.kill(pid, 0)  # Check if process exists
                        if time.time() - start_time > timeout:
                            print(f"Timeout waiting for PID {pid}, forcing termination", file=sys.stderr)
                            try:
                                os.kill(pid, signal.SIGKILL)
                            except:
                                pass
                            break
                        time.sleep(0.5)
                except ProcessLookupError:
                    pass  # Process already stopped
            
            # Clean up PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
            
            self.running = False
            print("All workers stopped", file=sys.stderr)
            
        except Exception as e:
            print(f"Error stopping workers: {e}", file=sys.stderr)
    
    def get_active_workers(self) -> int:
        """Get count of active workers"""
        if not self.pid_file.exists():
            return 0
        
        try:
            with open(self.pid_file, "r") as f:
                data = json.load(f)
                pids = data.get("pids", [])
            
            # Check which PIDs are still alive
            active = 0
            for pid in pids:
                try:
                    os.kill(pid, 0)  # Signal 0 checks if process exists
                    active += 1
                except ProcessLookupError:
                    pass
            
            return active
        except Exception:
            return 0

