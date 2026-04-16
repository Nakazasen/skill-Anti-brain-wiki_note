import argparse
import json
import subprocess
import sys
from pathlib import Path

# Thêm thư mục chứa abw_runner.py vào sys.path để import abw_accept an toàn
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import abw_accept


def run_command(command, workspace):
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=workspace,
            capture_output=True,
            text=True
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e)
        }


def main():
    parser = argparse.ArgumentParser(description="Minimal ABW Runner: Run command and evaluate.")
    parser.add_argument("--workspace", default=".", help="Workspace directory")
    parser.add_argument("--request", required=True, help="Path to acceptance request JSON")
    parser.add_argument("-c", "--command", required=True, help="Command to execute")
    parser.add_argument("--no-log", action="store_true", help="Do not append .brain/acceptance_log.jsonl")
    
    args = parser.parse_args()
    
    # 1. Thực thi command
    cmd_result = run_command(args.command, args.workspace)
    
    # 2. Thực thi đánh giá abw_accept
    try:
        eval_result = abw_accept.evaluate_file(args.workspace, args.request, write_log=not args.no_log)
    except Exception as e:
        eval_result = {"status": "error", "error": str(e)}

    # 3. Gộp Output
    final_output = {
        "runner_status": "completed",
        "command_exit_code": cmd_result["exit_code"],
        "command_stdout": cmd_result["stdout"],
        "command_stderr": cmd_result["stderr"],
        "evaluation": eval_result
    }
    
    print(json.dumps(final_output, ensure_ascii=False, indent=2, sort_keys=True))
    
    if eval_result.get("status") == "error":
        sys.exit(1)
    if eval_result.get("verdict") == "pass":
        sys.exit(0)
    sys.exit(2)


if __name__ == "__main__":
    main()
