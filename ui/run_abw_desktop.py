import sys
import os
import time
import subprocess
import requests
import socket
import argparse
import logging
import traceback
from pathlib import Path

from release_support import APP_VERSION, configure_file_logger, log_dir


LOGGER = configure_file_logger("abw_admin.launcher", "app.log")


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def get_available_port(start_port=8000):
    port = start_port
    while port < start_port + 10:
        if not is_port_in_use(port):
            return port
        port += 1
    return None

def start_api(port, env):
    api_url = f"http://127.0.0.1:{port}"
    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "--api-server", "--port", str(port)]
    else:
        cmd = [sys.executable, "-m", "uvicorn", "abw.api:app", "--port", str(port), "--host", "127.0.0.1"]
    api_log_path = log_dir() / "api.log"
    api_log_path.parent.mkdir(parents=True, exist_ok=True)
    api_log = api_log_path.open("a", encoding="utf-8")
    api_log.write(f"\n--- Starting ABW API v{APP_VERSION} on {api_url} ---\n")
    api_log.flush()
    return subprocess.Popen(
        cmd,
        env=env,
        stdout=api_log,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    ), api_url, api_log


def wait_for_health(api_process, api_url, max_retries=20):
    for _ in range(max_retries):
        if api_process.poll() is not None:
            return False, "API process exited prematurely."
        try:
            resp = requests.get(f"{api_url}/health", timeout=1)
            if resp.status_code == 200:
                return True, "API is ready."
        except Exception:
            pass
        time.sleep(0.5)
    return False, "API failed to start or health check timed out."


def terminate_process(process):
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except Exception:
        process.kill()


def resolve_paths(env):
    current_dir = Path(__file__).parent.resolve()
    if (current_dir / "main.py").exists() and (current_dir.parent / "src" / "abw").exists():
        src_path = str(current_dir.parent / "src")
        ui_script = str(current_dir / "main.py")
    else:
        src_path = str(current_dir)
        if (current_dir / "ui" / "main.py").exists():
            ui_script = str(current_dir / "ui" / "main.py")
        else:
            ui_script = str(current_dir / "main.py")

    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{src_path};{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = src_path
    return ui_script


def main(argv=None):
    parser = argparse.ArgumentParser(description="Launch ABW Admin Desktop and its local API.")
    parser.add_argument("--smoke", action="store_true", help="Start the API, verify /health, then shut down cleanly.")
    parser.add_argument("--api-server", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=8000, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.api_server:
        import uvicorn
        from abw.api import app as api_app

        LOGGER.info("Starting embedded API server on port %s", args.port)
        uvicorn.run(api_app, host="127.0.0.1", port=args.port)
        return 0

    # 1. Find a port
    port = get_available_port(8000)
    if port is None:
        message = "Could not find an available port between 8000 and 8009."
        LOGGER.error(message)
        print(f"Error: {message}")
        return 1
    
    api_url = f"http://127.0.0.1:{port}"
    print(f"Starting ABW API on {api_url}...")

    # Detect if we are running from source repo or packaged app
    env = os.environ.copy()
    resolve_paths(env)
    api_process = None
    api_log = None
    # 3. Wait for /health
    try:
        api_process, api_url, api_log = start_api(port, env)
        print("Waiting for API to be ready...")
        ready, message = wait_for_health(api_process, api_url)
        if not ready:
            LOGGER.error(message)
            print(f"Error: {message}")
            terminate_process(api_process)
            return 1

        print(message)
        if args.smoke:
            print("Smoke health check passed. Closing API cleanly.")
            terminate_process(api_process)
            return 0

        print("Launching UI...")

        # 4. Launch UI
        env["ABW_API_URL"] = api_url
        os.environ.update(env)
        from main import main as run_ui_main

        return run_ui_main()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        LOGGER.critical("Launcher crash: %s\n%s", exc, traceback.format_exc())
        print(f"Error: ABW Admin startup failed. See logs/app.log. {exc}")
        return 1
    finally:
        print("Shutting down API server...")
        if api_process is not None:
            terminate_process(api_process)
        if api_log is not None:
            api_log.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
