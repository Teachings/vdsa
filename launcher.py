#!/usr/bin/env python3
import sys
import subprocess
import signal
import time
from pathlib import Path

# Configuration
CONDA_ENV_NAME = "vdsa"
PROCESSES = {
    "stt": "stt/main.py",
    "dsa": "langgrapgh_dynamic_agent/dsa.py"
}

def get_conda_python():
    """Find Conda Python executable path"""
    try:
        result = subprocess.run(
            ["conda", "run", "-n", CONDA_ENV_NAME, "which", "python"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print(f"❌ Conda environment '{CONDA_ENV_NAME}' not found or Conda not installed")
        sys.exit(1)

def run_service(name, script_path, python_exec):
    """Run a service with logging and error handling"""
    print(f"🚀 Starting {name} service...")
    log_file = Path(f"logs/{name}.log")
    log_file.parent.mkdir(exist_ok=True)
    
    try:
        return subprocess.Popen(
            [python_exec, "-u", script_path],
            stdout=open(log_file, "a"),
            stderr=subprocess.STDOUT,
            bufsize=0,
            start_new_session=True
        )
    except Exception as e:
        print(f"❌ Failed to start {name}: {str(e)}")
        sys.exit(1)

def main():
    python_exec = get_conda_python()
    print(f"✅ Using Python from Conda environment: {python_exec}")
    
    processes = {}
    for name, script in PROCESSES.items():
        processes[name] = run_service(name, script, python_exec)
    
    print("\n🌈 Both services running! Press Ctrl+C to stop\n")
    print(f"📁 Logs being written to:")
    for name in PROCESSES:
        print(f"  - logs/{name}.log")
    
    # Keep main process alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        for name, proc in processes.items():
            print(f"⏳ Stopping {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("✅ All services stopped")

if __name__ == "__main__":
    main()