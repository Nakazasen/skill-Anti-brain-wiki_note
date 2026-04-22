import sys
from pathlib import Path


scripts_dir = Path(__file__).resolve().parent / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import ai_runner as runner


if __name__ == "__main__":
    raise SystemExit(runner.main())
