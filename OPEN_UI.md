# 🚀 How to Access the Web UI

## Option 1: Use the Helper Script (Recommended)

```bash
python start_ui.py
```

This will:
- Start the web server
- Automatically open your browser
- Display the dashboard

## Option 2: Manual Start

1. **Start the web server:**
   ```bash
   python -m queuectl.cli web
   ```

2. **Open your browser and go to:**
   ```
   http://127.0.0.1:5000
   ```
   or
   ```
   http://localhost:5000
   ```

## Option 3: Start in Background and Open Browser

1. **Start server in background:**
   ```bash
   python -m queuectl.cli web
   ```
   (Leave this terminal open)

2. **Open browser manually:**
   - Chrome/Edge: Press `Win + R`, type `http://127.0.0.1:5000`, press Enter
   - Or copy this URL: `http://127.0.0.1:5000`
   - Or click this link: [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Troubleshooting

### If you see "Connection Refused":
1. Make sure the server is running
2. Check if port 5000 is available: `netstat -ano | findstr :5000`
3. Try a different port: `python -m queuectl.cli web --port 8080`

### If the page loads but shows errors:
1. Check browser console (F12)
2. Make sure workers are running: `queuectl worker start --count 1`
3. Check if jobs exist: `queuectl status`

### If port 5000 is busy:
```bash
python -m queuectl.cli web --port 8080
```
Then open: `http://127.0.0.1:8080`

## Quick Test

1. Start server: `python -m queuectl.cli web`
2. Open browser: Go to `http://127.0.0.1:5000`
3. Start workers: `queuectl worker start --count 1` (in another terminal)
4. Enqueue a job from the UI or CLI
5. Watch it process in real-time!

## What You Should See

- 📊 Statistics cards showing job counts
- 📋 List of all jobs
- ➕ Form to enqueue new jobs
- ⚙️ Configuration display
- 🔄 Auto-refresh every 2 seconds

