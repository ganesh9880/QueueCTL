#!/usr/bin/env python3
"""Helper script to start the web UI and open it in browser"""

import webbrowser
import time
import subprocess
import sys
from threading import Timer

def open_browser(url):
    """Open browser after a short delay"""
    time.sleep(2)  # Wait for server to start
    print(f"\n{'='*60}")
    print(f"Opening browser at: {url}")
    print(f"{'='*60}\n")
    webbrowser.open(url)

if __name__ == "__main__":
    url = "http://127.0.0.1:5000"
    
    print("=" * 60)
    print("Starting queuectl Web UI...")
    print("=" * 60)
    print(f"\nServer will start at: {url}")
    print("Browser will open automatically in 2 seconds...")
    print("\nPress Ctrl+C to stop the server\n")
    
    # Open browser in background thread
    Timer(2.0, open_browser, args=(url,)).start()
    
    # Start the web server
    try:
        from queuectl.web import run_web_ui
        run_web_ui(host='127.0.0.1', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
    except Exception as e:
        print(f"\nError starting server: {e}")
        print("\nTry running manually: python -m queuectl.cli web")
        sys.exit(1)

