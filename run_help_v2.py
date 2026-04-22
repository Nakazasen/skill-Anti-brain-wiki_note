import json
import sys
import os
from pathlib import Path

# Ensure we can import from the current directory
sys.path.insert(0, os.getcwd())

from scripts import abw_runner

def main():
    payload = {
        "task": "/abw-ask \"help\"",
        "task_kind": "execution"
    }
    
    # Force UTF-8 for stdout
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    
    result = abw_runner.dispatch_request(
        task=payload["task"],
        task_kind=payload.get("task_kind", "execution")
    )
    
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
