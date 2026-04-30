# ABW Admin Desktop UI

A thin PySide6 desktop application for interacting with the ABW local API.

## Requirements

- Python 3.10+
- `PySide6`
- `requests`

## How to Run (One-Click)

For a one-click experience that starts both the API and the UI automatically:
```bash
py ui/run_abw_desktop.py
```
This script will:
1. Find an available port starting from 8000.
2. Launch the ABW API in the background.
3. Wait for the API health check to pass.
4. Launch the PySide6 UI with the correct API URL.
5. Shut down the API automatically when the UI is closed.

## How to Build Executable

To package the application into a standalone Windows folder:

1. Install build dependencies:
   ```bash
   pip install pyinstaller PySide6 requests uvicorn fastapi
   ```

2. Run the build script:
   ```bash
   scripts\build_desktop.bat
   ```

3. The v1.0.1 pilot output is `dist/ABW-Admin-v1.0.1/`. You can run `ABW-Admin-v1.0.1.exe` from that folder.

## Smoke Test

Run the desktop startup smoke test without opening the UI:
```bash
py scripts/desktop_smoke.py
```
This starts the local API, checks `/health`, and shuts the API down cleanly.

## Manual Execution (Advanced)

## Features

- **Top Bar**: Configure the API URL.
- **Left Panel**: Set the workspace path and run diagnostics (Health, Inspect, Gaps, Trend, Improve).
- **Center Panel**: View results in formatted JSON.
- **Right Panel**: Perform quick actions like `cleanup-drafts` or `archive-stale` in dry-run mode.

## Troubleshooting

- If the application fails to connect, check if the API URL in the top bar matches your running server.
- Errors from the API will be displayed in a popup message.
