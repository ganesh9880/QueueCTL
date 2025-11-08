"""Configuration management for queuectl"""

import json
import os
from pathlib import Path
from typing import Dict, Any

CONFIG_DIR = Path.home() / ".queuectl"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_CONFIG = {
    "max_retries": 3,
    "backoff_base": 2,
    "db_path": str(CONFIG_DIR / "jobs.db"),
    "worker_pid_file": str(CONFIG_DIR / "workers.pid"),
}


def ensure_config_dir():
    """Ensure configuration directory exists"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Dict[str, Any]:
    """Load configuration from file or return defaults"""
    ensure_config_dir()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                user_config = json.load(f)
                config = {**DEFAULT_CONFIG, **user_config}
                return config
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]):
    """Save configuration to file"""
    ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_config(key: str, default=None):
    """Get a specific configuration value"""
    config = load_config()
    return config.get(key, default)


def set_config(key: str, value: Any):
    """Set a specific configuration value"""
    config = load_config()
    config[key] = value
    save_config(config)

