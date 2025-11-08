# queuectl - CLI-based Background Job Queue System

A production-grade, CLI-based background job queue system built with Python. This system manages background jobs with worker processes, handles retries using exponential backoff, and maintains a Dead Letter Queue (DLQ) for permanently failed jobs.

## 🚀 Features

- ✅ **Job Management**: Enqueue, list, and track jobs through their lifecycle
- ✅ **Worker Processes**: Run multiple worker processes in parallel
- ✅ **Retry Mechanism**: Automatic retries with exponential backoff
- ✅ **Dead Letter Queue**: Handle permanently failed jobs
- ✅ **Persistent Storage**: SQLite-based storage that survives restarts
- ✅ **Graceful Shutdown**: Workers finish current jobs before exiting
- ✅ **Configuration Management**: Configurable retry count and backoff settings
- ✅ **Thread-Safe**: Prevents duplicate job processing with locking

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd flam
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install queuectl:**
   ```bash
   pip install -e .
   ```

   Alternatively, you can run it directly without installation:
   ```bash
   python -m queuectl.cli --help
   ```

## 🚀 Quick Start

1. **Enqueue your first job:**
   ```bash
   queuectl enqueue '{"id":"hello","command":"echo Hello World"}'
   ```

2. **Start a worker:**
   ```bash
   queuectl worker start --count 1
   ```

3. **Check status:**
   ```bash
   queuectl status
   ```

4. **View completed jobs:**
   ```bash
   queuectl list --state completed
   ```

5. **Stop workers when done:**
   ```bash
   queuectl worker stop
   ```

6. **Start Web UI (Optional):**
   ```bash
   queuectl web
   ```
   Then open http://127.0.0.1:5000 in your browser

## 🎯 Usage

### Basic Commands

#### Enqueue a Job

**Linux/Mac:**
```bash
queuectl enqueue '{"id":"job1","command":"echo Hello World"}'
```

**Windows PowerShell:**
```powershell
queuectl enqueue '{"id":"job1","command":"echo Hello World"}'
```

**Windows CMD:**
```cmd
queuectl enqueue "{\"id\":\"job1\",\"command\":\"echo Hello World\"}"
```

You can also specify custom max retries:
```bash
queuectl enqueue '{"id":"job2","command":"sleep 5","max_retries":5}'
```

#### Start Workers

Start a single worker:
```bash
queuectl worker start
```

Start multiple workers:
```bash
queuectl worker start --count 3
```

#### Stop Workers

```bash
queuectl worker stop
```

Workers will gracefully finish their current jobs before shutting down.

#### Check Status

```bash
queuectl status
```

Output example:
```
=== Queue Status ===
Active Workers: 2

Job States:
  Pending    : 5
  Processing : 2
  Completed  : 10
  Failed     : 1
  Dead       : 3

Total Jobs: 21
```

#### List Jobs

List all jobs:
```bash
queuectl list
```

Filter by state:
```bash
queuectl list --state pending
queuectl list --state completed
queuectl list --state dead
```

Limit results:
```bash
queuectl list --limit 10
```

#### Dead Letter Queue

List jobs in DLQ:
```bash
queuectl dlq list
```

Retry a job from DLQ:
```bash
queuectl dlq retry job1
```

#### Configuration

View all configuration:
```bash
queuectl config get
```

Get a specific config value:
```bash
queuectl config get max_retries
# or with hyphen (both work)
queuectl config get max-retries
```

Set configuration values:
```bash
queuectl config set max_retries 5
queuectl config set backoff_base 3
```

Note: Both hyphen and underscore are supported (e.g., `max-retries` or `max_retries`).

#### Web UI Dashboard

Start the web UI dashboard:
```bash
queuectl web
```

Or with custom host/port:
```bash
queuectl web --host 0.0.0.0 --port 8080
```

Then open your browser and navigate to http://127.0.0.1:5000 (or your custom port).

**Features:**
- 📊 Real-time job statistics dashboard
- 📋 View and filter jobs by state
- ➕ Enqueue new jobs from the UI
- 🔄 Auto-refresh every 2 seconds
- 💀 DLQ management with retry functionality
- ⚙️ View and manage configuration

## 📊 Job Lifecycle

Jobs progress through the following states:

| State | Description |
|-------|-------------|
| `pending` | Waiting to be picked up by a worker |
| `processing` | Currently being executed by a worker |
| `completed` | Successfully executed |
| `failed` | Failed, but retryable (will retry with backoff) |
| `dead` | Permanently failed (moved to DLQ after max retries) |

### Job Execution Flow

1. **Enqueue**: Job is created with state `pending`
2. **Acquire**: Worker acquires the job (state → `processing`)
3. **Execute**: Worker executes the command
4. **Success**: Job state → `completed`
5. **Failure**: Job state → `failed`, increments attempts
6. **Retry**: After exponential backoff delay, job becomes `pending` again
7. **DLQ**: After `max_retries` failures, job state → `dead`

### Exponential Backoff

Failed jobs are retried with exponential backoff. The delay is calculated as:

```
delay = backoff_base ^ attempts seconds
```

Default values:
- `backoff_base`: 2 (so delays are 1s, 2s, 4s, 8s, ...)
- `max_retries`: 3

## 🏗️ Architecture

### Components

1. **CLI Interface** (`queuectl/cli.py`)
   - Command-line interface using Click
   - Handles all user commands

2. **Storage Layer** (`queuectl/storage.py`)
   - SQLite-based persistent storage
   - Thread-safe job operations
   - Job locking to prevent duplicate processing

3. **Job Model** (`queuectl/job.py`)
   - Job representation and execution logic
   - Retry and backoff calculations
   - State management

4. **Worker Manager** (`queuectl/worker.py`)
   - Manages worker processes
   - Handles graceful shutdown
   - Process coordination

5. **Configuration** (`queuectl/config.py`)
   - Configuration management
   - Persistent config storage in `~/.queuectl/config.json`

### Data Persistence

- **Database**: SQLite database stored at `~/.queuectl/jobs.db`
- **Configuration**: JSON file at `~/.queuectl/config.json`
- **Worker PIDs**: JSON file at `~/.queuectl/workers.pid`

### Concurrency & Locking

- Workers use database-level locking to prevent duplicate job processing
- The `acquire_job()` method atomically changes job state from `pending` to `processing`
- Only one worker can acquire a specific job at a time

## 🧪 Testing

### Validation Script

Run the validation script to test core functionality:

```bash
python validate.py
```

This script tests:
1. ✅ Job enqueuing
2. ✅ Status command
3. ✅ Worker job completion
4. ✅ Retry and DLQ functionality
5. ✅ Job persistence
6. ✅ List commands
7. ✅ Configuration management

### Manual Testing

#### Test 1: Basic Job Completion

```bash
# Enqueue a job
queuectl enqueue '{"id":"test1","command":"echo success"}'

# Start a worker
queuectl worker start --count 1

# Wait a few seconds, then check status
queuectl status

# Check job state
queuectl list --state completed

# Stop worker
queuectl worker stop
```

#### Test 2: Retry and DLQ

```bash
# Set max retries to 2 for faster testing
queuectl config set max-retries 2

# Enqueue a failing job
queuectl enqueue '{"id":"test2","command":"nonexistentcommand"}'

# Start a worker
queuectl worker start --count 1

# Wait for retries (check status periodically)
queuectl status

# After max retries, check DLQ
queuectl dlq list

# Retry the job
queuectl dlq retry test2

# Stop worker
queuectl worker stop
```

#### Test 3: Multiple Workers

```bash
# Enqueue multiple jobs
queuectl enqueue '{"id":"job1","command":"sleep 2"}'
queuectl enqueue '{"id":"job2","command":"sleep 2"}'
queuectl enqueue '{"id":"job3","command":"sleep 2"}'

# Start 3 workers
queuectl worker start --count 3

# Watch jobs get processed in parallel
queuectl status

# Stop workers
queuectl worker stop
```

#### Test 4: Persistence

```bash
# Enqueue a job
queuectl enqueue '{"id":"persistent1","command":"echo test"}'

# Stop any workers
queuectl worker stop

# Restart workers (simulates system restart)
queuectl worker start --count 1

# Job should still exist and be processed
queuectl list

# Stop worker
queuectl worker stop
```

## 📁 Project Structure

```
flam/
├── queuectl/
│   ├── __init__.py          # Package initialization
│   ├── cli.py               # CLI interface
│   ├── storage.py           # SQLite persistence
│   ├── job.py               # Job model and execution
│   ├── worker.py            # Worker process management
│   └── config.py            # Configuration management
├── requirements.txt         # Python dependencies
├── setup.py                 # Package setup
├── validate.py              # Validation script
└── README.md                # This file
```

## ⚙️ Configuration

Default configuration values:

```json
{
  "max_retries": 3,
  "backoff_base": 2,
  "db_path": "~/.queuectl/jobs.db",
  "worker_pid_file": "~/.queuectl/workers.pid"
}
```

Configuration is stored in `~/.queuectl/config.json` and can be modified using the `queuectl config` commands.

## 🔧 Troubleshooting

### Workers not starting

- Check if workers are already running: `queuectl status`
- Check for stale PID files: `ls ~/.queuectl/workers.pid`
- Manually remove PID file if needed: `rm ~/.queuectl/workers.pid`

### Jobs stuck in processing

- This can happen if a worker crashes while processing
- Reset the job state manually in the database or restart workers
- Future enhancement: Add timeout handling for stuck jobs

### Database locked errors

- Ensure only one process accesses the database at a time
- Check for zombie worker processes: `ps aux | grep queuectl`

## 🎓 Assumptions & Trade-offs

### Assumptions

1. **Command Execution**: Commands are executed in a shell environment
2. **Exit Codes**: Exit code 0 = success, non-zero = failure
3. **Single Machine**: Designed for single-machine deployment
4. **File System**: Relies on file system for persistence and locking

### Trade-offs

1. **SQLite over PostgreSQL/MySQL**: 
   - Simpler setup, no external dependencies
   - Good enough for single-machine deployment
   - Trade-off: Limited scalability

2. **File-based PID tracking**:
   - Simple implementation
   - Trade-off: May have stale PIDs if workers crash

3. **No job timeout by default**:
   - Keeps implementation simple
   - Trade-off: Jobs can hang indefinitely

4. **Synchronous job execution**:
   - Easier to manage and debug
   - Trade-off: Long-running jobs block workers

## 🚧 Future Enhancements

Potential improvements (not implemented):

- [ ] Job timeout handling
- [ ] Job priority queues
- [ ] Scheduled/delayed jobs (`run_at` field)
- [ ] Job output logging and retrieval
- [ ] Metrics and execution statistics
- [x] Web dashboard for monitoring ✅ **Implemented!**
- [ ] Distributed deployment support
- [ ] Job dependencies
- [ ] Job cancellation

## 📝 License

This project is created for internship assignment purposes.

## 👤 Author

Created as part of an internship assignment.

## 🤝 Contributing

This is an assignment project, but feedback and suggestions are welcome!

---

## ✅ Checklist

- [x] Working CLI application (`queuectl`)
- [x] Persistent job storage (SQLite)
- [x] Multiple worker support
- [x] Retry mechanism with exponential backoff
- [x] Dead Letter Queue
- [x] Configuration management
- [x] Clean CLI interface with help texts
- [x] Comprehensive README.md
- [x] Code structured with clear separation of concerns
- [x] Validation script to test core flows
- [x] **Web UI dashboard** 🎉 (Bonus feature)

