import json
import os
import sys

import abw_entry
import abw_output


def main():
    os.environ["ABW_AGENT_MODE"] = "1"
    os.environ["ABW_EXECUTION_PATH"] = "ai_runner"
    os.environ.pop("ABW_CLI_MODE", None)

    raw_input = sys.stdin.read()
    if not raw_input.strip():
        return 0

    payload = json.loads(raw_input)
    task = str(payload.get("task") or "").strip()
    task_kind = str(payload.get("task_kind") or "execution").strip() or "execution"
    level = abw_output.normalize_user_level(payload.get("level"))

    result = abw_entry.execute_command("/abw-ask", task=task, task_kind=task_kind)
    final = abw_entry.final_output(result)
    print(abw_output.render(final, level=level))
    return 0 if final.get("binding_status") != "rejected" and final.get("runner_status") != "blocked" else 3


if __name__ == "__main__":
    raise SystemExit(main())
