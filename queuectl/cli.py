"""CLI interface for queuectl"""

import click
import json
import sys
from datetime import datetime
from typing import Optional

from queuectl.storage import JobStorage
from queuectl.worker import WorkerManager
from queuectl.config import get_config, set_config, load_config


@click.group()
def cli():
    """queuectl - CLI-based background job queue system"""
    pass


@cli.command()
@click.argument("job_json", type=str)
def enqueue(job_json: str):
    """Enqueue a new job to the queue
    
    Example: queuectl enqueue '{"id":"job1","command":"sleep 2"}'
    """
    try:
        job_data = json.loads(job_json)
        job_id = job_data.get("id")
        command = job_data.get("command")
        max_retries = job_data.get("max_retries", get_config("max_retries", 3))
        
        if not job_id or not command:
            click.echo("Error: 'id' and 'command' are required fields", err=True)
            sys.exit(1)
        
        storage = JobStorage()
        
        # Check if job already exists
        if storage.get_job(job_id):
            click.echo(f"Error: Job '{job_id}' already exists", err=True)
            sys.exit(1)
        
        job = storage.create_job(job_id, command, max_retries)
        click.echo(f"Job '{job_id}' enqueued successfully")
        click.echo(f"  Command: {command}")
        click.echo(f"  State: {job['state']}")
        click.echo(f"  Max retries: {max_retries}")
        
    except json.JSONDecodeError:
        click.echo("Error: Invalid JSON format", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def worker():
    """Manage worker processes"""
    pass


@worker.command()
@click.option("--count", default=1, type=int, help="Number of workers to start")
def start(count: int):
    """Start worker processes"""
    if count < 1:
        click.echo("Error: Worker count must be at least 1", err=True)
        sys.exit(1)
    
    manager = WorkerManager()
    manager.start_workers(count)


@worker.command()
def stop():
    """Stop all running workers gracefully"""
    manager = WorkerManager()
    manager.stop_workers()


@cli.command()
def status():
    """Show summary of all job states and active workers"""
    storage = JobStorage()
    manager = WorkerManager()
    
    stats = storage.get_stats()
    active_workers = manager.get_active_workers()
    
    click.echo("=== Queue Status ===")
    click.echo(f"Active Workers: {active_workers}")
    click.echo("\nJob States:")
    
    states = ["pending", "processing", "completed", "failed", "dead"]
    for state in states:
        count = stats.get(state, 0)
        click.echo(f"  {state.capitalize():12}: {count}")
    
    total = sum(stats.values())
    click.echo(f"\nTotal Jobs: {total}")


@cli.command()
@click.option("--state", type=click.Choice(["pending", "processing", "completed", "failed", "dead"]), 
              help="Filter jobs by state")
@click.option("--limit", default=20, type=int, help="Maximum number of jobs to display")
def list(state: Optional[str], limit: int):
    """List jobs, optionally filtered by state"""
    storage = JobStorage()
    jobs = storage.list_jobs(state=state, limit=limit)
    
    if not jobs:
        click.echo("No jobs found")
        return
    
    click.echo(f"=== Jobs ({len(jobs)} shown) ===")
    for job in jobs:
        click.echo(f"\nID: {job['id']}")
        click.echo(f"  Command: {job['command']}")
        click.echo(f"  State: {job['state']}")
        click.echo(f"  Attempts: {job['attempts']}/{job['max_retries']}")
        click.echo(f"  Created: {job['created_at']}")
        if job.get('next_retry_at'):
            click.echo(f"  Next Retry: {job['next_retry_at']}")
        if job.get('error_message'):
            click.echo(f"  Error: {job['error_message']}")


@cli.group()
def dlq():
    """Manage Dead Letter Queue"""
    pass


@dlq.command("list")
@click.option("--limit", default=20, type=int, help="Maximum number of jobs to display")
def dlq_list(limit: int):
    """List jobs in the Dead Letter Queue"""
    storage = JobStorage()
    jobs = storage.get_dlq_jobs()
    
    if limit:
        jobs = jobs[:limit]
    
    if not jobs:
        click.echo("Dead Letter Queue is empty")
        return
    
    click.echo(f"=== Dead Letter Queue ({len(jobs)} jobs) ===")
    for job in jobs:
        click.echo(f"\nID: {job['id']}")
        click.echo(f"  Command: {job['command']}")
        click.echo(f"  Attempts: {job['attempts']}/{job['max_retries']}")
        click.echo(f"  Failed at: {job['updated_at']}")
        if job.get('error_message'):
            click.echo(f"  Error: {job['error_message']}")


@dlq.command()
@click.argument("job_id", type=str)
def retry(job_id: str):
    """Retry a job from the Dead Letter Queue"""
    storage = JobStorage()
    job = storage.get_job(job_id)
    
    if not job:
        click.echo(f"Error: Job '{job_id}' not found", err=True)
        sys.exit(1)
    
    if job["state"] != "dead":
        click.echo(f"Error: Job '{job_id}' is not in the Dead Letter Queue (state: {job['state']})", err=True)
        sys.exit(1)
    
    updated_job = storage.reset_job_for_retry(job_id)
    if updated_job:
        click.echo(f"Job '{job_id}' has been reset and will be retried")
        click.echo(f"  State: {updated_job['state']}")
        click.echo(f"  Attempts reset to: {updated_job['attempts']}")
    else:
        click.echo(f"Error: Failed to reset job '{job_id}'", err=True)
        sys.exit(1)


@cli.group()
def config():
    """Manage configuration"""
    pass


@config.command("get")
@click.argument("key", type=str, required=False)
def config_get(key: Optional[str]):
    """Get configuration value(s)
    
    Examples:
        queuectl config get
        queuectl config get max_retries
        queuectl config get max-retries  (hyphens are converted to underscores)
    """
    if key:
        # Normalize key: convert hyphens to underscores
        key = key.replace("-", "_")
        value = get_config(key)
        if value is None:
            click.echo(f"Error: Configuration key '{key}' not found", err=True)
            sys.exit(1)
        click.echo(f"{key} = {value}")
    else:
        config = load_config()
        click.echo("=== Configuration ===")
        for k, v in config.items():
            click.echo(f"{k} = {v}")


@config.command("set")
@click.argument("key", type=str)
@click.argument("value", type=str)
def config_set(key: str, value: str):
    """Set a configuration value
    
    Examples:
        queuectl config set max_retries 5
        queuectl config set backoff_base 3
    """
    # Normalize key: convert hyphens to underscores
    key = key.replace("-", "_")
    
    # Try to convert value to appropriate type
    try:
        # Try integer
        if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
            value = int(value)
        # Try float
        elif '.' in value and value.replace('.', '').replace('-', '').isdigit():
            value = float(value)
        # Try boolean
        elif value.lower() in ('true', 'false'):
            value = value.lower() == 'true'
    except:
        pass  # Keep as string
    
    set_config(key, value)
    click.echo(f"Set {key} = {value}")


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=5000, type=int, help="Port to bind to")
@click.option("--debug", is_flag=True, help="Enable debug mode")
def web(host: str, port: int, debug: bool):
    """Start the web UI dashboard"""
    from queuectl.web import run_web_ui
    run_web_ui(host=host, port=port, debug=debug)


def main():
    """Entry point for CLI"""
    cli()


if __name__ == "__main__":
    main()

