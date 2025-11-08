"""Web UI dashboard for queuectl"""

from flask import Flask, render_template, jsonify, request
import json
import os
from pathlib import Path
from queuectl.storage import JobStorage
from queuectl.worker import WorkerManager
from queuectl.config import get_config, set_config, load_config

# Get the directory where this file is located
BASE_DIR = Path(__file__).parent
TEMPLATE_DIR = BASE_DIR / 'templates'

app = Flask(__name__, template_folder=str(TEMPLATE_DIR))


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/api/status')
def api_status():
    """Get queue status"""
    storage = JobStorage()
    manager = WorkerManager()
    
    stats = storage.get_stats()
    active_workers = manager.get_active_workers()
    
    return jsonify({
        'active_workers': active_workers,
        'stats': {
            'pending': stats.get('pending', 0),
            'processing': stats.get('processing', 0),
            'completed': stats.get('completed', 0),
            'failed': stats.get('failed', 0),
            'dead': stats.get('dead', 0),
        },
        'total': sum(stats.values())
    })


@app.route('/api/jobs')
def api_jobs():
    """Get jobs list"""
    storage = JobStorage()
    state = request.args.get('state')
    limit = request.args.get('limit', 100, type=int)
    
    jobs = storage.list_jobs(state=state, limit=limit)
    return jsonify({'jobs': jobs})


@app.route('/api/job/<job_id>')
def api_job(job_id):
    """Get specific job details"""
    storage = JobStorage()
    job = storage.get_job(job_id)
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify({'job': job})


@app.route('/api/dlq')
def api_dlq():
    """Get DLQ jobs"""
    storage = JobStorage()
    jobs = storage.get_dlq_jobs()
    return jsonify({'jobs': jobs})


@app.route('/api/dlq/<job_id>/retry', methods=['POST'])
def api_dlq_retry(job_id):
    """Retry a job from DLQ"""
    storage = JobStorage()
    job = storage.get_job(job_id)
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    if job['state'] != 'dead':
        return jsonify({'error': f"Job is not in DLQ (state: {job['state']})"}), 400
    
    updated_job = storage.reset_job_for_retry(job_id)
    if updated_job:
        return jsonify({'success': True, 'job': updated_job})
    else:
        return jsonify({'error': 'Failed to reset job'}), 500


@app.route('/api/enqueue', methods=['POST'])
def api_enqueue():
    """Enqueue a new job"""
    data = request.get_json()
    
    job_id = data.get('id')
    command = data.get('command')
    max_retries = data.get('max_retries', get_config('max_retries', 3))
    
    if not job_id or not command:
        return jsonify({'error': "'id' and 'command' are required"}), 400
    
    storage = JobStorage()
    
    # Check if job already exists
    if storage.get_job(job_id):
        return jsonify({'error': f"Job '{job_id}' already exists"}), 400
    
    job = storage.create_job(job_id, command, max_retries)
    return jsonify({'success': True, 'job': job})


@app.route('/api/config')
def api_config():
    """Get configuration"""
    config = load_config()
    return jsonify({'config': config})


@app.route('/api/config', methods=['POST'])
def api_config_set():
    """Set configuration"""
    data = request.get_json()
    key = data.get('key')
    value = data.get('value')
    
    if not key:
        return jsonify({'error': "'key' is required"}), 400
    
    # Normalize key
    key = key.replace('-', '_')
    
    set_config(key, value)
    return jsonify({'success': True, 'key': key, 'value': value})


def run_web_ui(host='127.0.0.1', port=5000, debug=False):
    """Run the web UI server"""
    print(f"Starting queuectl Web UI at http://{host}:{port}")
    print(f"Open your browser and navigate to http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_web_ui(debug=True)

