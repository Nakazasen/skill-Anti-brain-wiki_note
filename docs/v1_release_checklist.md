# ABW Admin v1.0.0 Internal Release Checklist

## Baseline Validation

- [ ] `py -m pytest`
- [ ] `py -m py_compile ui/main.py ui/run_abw_desktop.py`
- [ ] `py scripts/desktop_smoke.py`

## Desktop Release Readiness

- [ ] Persistent settings save and restore:
  - last workspace path
  - last API port
  - window size
  - recent workspaces
- [ ] Runtime logs are written:
  - `logs/app.log`
  - `logs/api.log`
- [ ] Startup failures are logged and shown with recoverable messages.
- [ ] Help > About shows version and build info.

## Packaging

- [ ] Run `scripts\build_desktop.bat`.
- [ ] Confirm output folder exists: `dist\ABW-Admin-v1.0.0\`.
- [ ] Confirm executable exists: `dist\ABW-Admin-v1.0.0\ABW-Admin-v1.0.0.exe`.

## Smoke Test

- [ ] Launch the app through `ui\run_abw_desktop.py`.
- [ ] Confirm `/health` returns `200`.
- [ ] Close the app and confirm the API process shuts down cleanly.

## Release Verdict

- [ ] PASS: all baseline, smoke, logging, settings, and packaging checks pass.
- [ ] PARTIAL: only non-blocking packaging or environment issues remain.
- [ ] FAIL: tests fail, app cannot start, health check fails, or shutdown leaves the API running.
