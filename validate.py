#!/usr/bin/env python3
"""Validation script to test core queuectl functionality"""

import subprocess
import time
import json
import sys
import os
from pathlib import Path

# Add queuectl to path
sys.path.insert(0, str(Path(__file__).parent))

from queuectl.storage import JobStorage
from queuectl.config import CONFIG_DIR

def run_command(cmd: list, capture_output=True):
    """Run a command and return result"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def test_enqueue():
    """Test 1: Basic job enqueuing"""
    print("\n=== Test 1: Enqueue Job ===")
    cmd = [
        sys.executable, "-m", "queuectl.cli", "enqueue",
        '{"id":"test1","command":"echo hello"}'
    ]
    success, stdout, stderr = run_command(cmd)
    if success:
        print("✅ Job enqueued successfully")
        return True
    else:
        print(f"❌ Failed: {stderr}")
        return False

def test_status():
    """Test 2: Status command"""
    print("\n=== Test 2: Status Command ===")
    cmd = [sys.executable, "-m", "queuectl.cli", "status"]
    success, stdout, stderr = run_command(cmd)
    if success:
        print("✅ Status command works")
        print(stdout)
        return True
    else:
        print(f"❌ Failed: {stderr}")
        return False

def test_worker_completion():
    """Test 3: Worker completes job successfully"""
    print("\n=== Test 3: Worker Completes Job ===")
    
    # Enqueue a simple job
    cmd = [
        sys.executable, "-m", "queuectl.cli", "enqueue",
        '{"id":"test3","command":"echo success"}'
    ]
    run_command(cmd)
    
    # Start a worker
    worker_cmd = [sys.executable, "-m", "queuectl.cli", "worker", "start", "--count", "1"]
    subprocess.Popen(worker_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for job to complete
    time.sleep(3)
    
    # Check job status
    storage = JobStorage()
    job = storage.get_job("test3")
    
    if job and job["state"] == "completed":
        print("✅ Job completed successfully")
        
        # Stop worker
        run_command([sys.executable, "-m", "queuectl.cli", "worker", "stop"])
        return True
    else:
        print(f"❌ Job not completed. State: {job['state'] if job else 'not found'}")
        run_command([sys.executable, "-m", "queuectl.cli", "worker", "stop"])
        return False

def test_retry_and_dlq():
    """Test 4: Failed job retries and moves to DLQ"""
    print("\n=== Test 4: Retry and DLQ ===")
    
    # Set max retries to 2 for faster testing
    run_command([
        sys.executable, "-m", "queuectl.cli", "config", "set", "max_retries", "2"
    ])
    
    # Enqueue a job that will fail
    cmd = [
        sys.executable, "-m", "queuectl.cli", "enqueue",
        '{"id":"test4","command":"nonexistentcommand12345"}'
    ]
    run_command(cmd)
    
    # Start a worker
    worker_cmd = [sys.executable, "-m", "queuectl.cli", "worker", "start", "--count", "1"]
    subprocess.Popen(worker_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for retries and DLQ
    print("Waiting for retries...")
    time.sleep(10)
    
    # Check job status
    storage = JobStorage()
    job = storage.get_job("test4")
    
    if job and job["state"] == "dead":
        print(f"✅ Job moved to DLQ after {job['attempts']} attempts")
        
        # Test DLQ list
        success, stdout, _ = run_command([
            sys.executable, "-m", "queuectl.cli", "dlq", "list"
        ])
        if success and "test4" in stdout:
            print("✅ DLQ list command works")
        
        # Stop worker
        run_command([sys.executable, "-m", "queuectl.cli", "worker", "stop"])
        return True
    else:
        print(f"❌ Job not in DLQ. State: {job['state'] if job else 'not found'}")
        run_command([sys.executable, "-m", "queuectl.cli", "worker", "stop"])
        return False

def test_persistence():
    """Test 5: Job persistence across restarts"""
    print("\n=== Test 5: Persistence ===")
    
    # Enqueue a job
    cmd = [
        sys.executable, "-m", "queuectl.cli", "enqueue",
        '{"id":"test5","command":"echo persistent"}'
    ]
    run_command(cmd)
    
    # Verify job exists
    storage = JobStorage()
    job1 = storage.get_job("test5")
    
    if not job1:
        print("❌ Job not found before restart simulation")
        return False
    
    # Create new storage instance (simulates restart)
    storage2 = JobStorage()
    job2 = storage2.get_job("test5")
    
    if job2 and job2["id"] == "test5":
        print("✅ Job persisted across storage instances")
        return True
    else:
        print("❌ Job not found after restart simulation")
        return False

def test_list_jobs():
    """Test 6: List jobs by state"""
    print("\n=== Test 6: List Jobs ===")
    
    success, stdout, _ = run_command([
        sys.executable, "-m", "queuectl.cli", "list", "--state", "completed"
    ])
    
    if success:
        print("✅ List command works")
        return True
    else:
        print("❌ List command failed")
        return False

def test_config():
    """Test 7: Configuration management"""
    print("\n=== Test 7: Configuration ===")
    
    # Set a config value
    success1, _, _ = run_command([
        sys.executable, "-m", "queuectl.cli", "config", "set", "max-retries", "5"
    ])
    
    # Get config value
    success2, stdout, _ = run_command([
        sys.executable, "-m", "queuectl.cli", "config", "get", "max_retries"
    ])
    
    if success1 and success2 and "5" in stdout:
        print("✅ Configuration management works")
        return True
    else:
        print("❌ Configuration management failed")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("queuectl Validation Script")
    print("=" * 50)
    
    tests = [
        test_enqueue,
        test_status,
        test_worker_completion,
        test_retry_and_dlq,
        test_persistence,
        test_list_jobs,
        test_config,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            results.append(False)
        time.sleep(1)
    
    print("\n" + "=" * 50)
    print("Test Results")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())

