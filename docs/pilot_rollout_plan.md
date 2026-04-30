# ABW Admin v1.0.1 Pilot Rollout Plan

## Pilot Group

- 3-5 internal users who already work with ABW workspaces.
- Include at least one engineering user, one documentation or operations user, and one less-frequent ABW user.
- Use non-critical or copied workspaces for pilot testing.

## Tasks To Test

- Launch the desktop app from the packaged build.
- Run Health against the default local API.
- Select a workspace and run Inspect, Gaps, Trend, and Improve.
- Run dry-run cleanup/archive actions only.
- Submit one bug, idea, or usability note through Help > Send Feedback.
- Export diagnostics after completing the session.
- Close the app and confirm the local API shuts down cleanly.

## Bug Reporting

- Use Help > Send Feedback for local feedback capture.
- Feedback is written only to local `feedback/feedback_*.json` files.
- Attach the diagnostics zip from the Export Diagnostics button when reporting a bug internally.
- Diagnostics are local-only and include logs, settings, and runtime manifest metadata.
- Do not upload sensitive workspace contents unless explicitly approved.

## Success Metrics

- 100% of pilot users can launch the app and pass Health.
- 80% or more can complete Inspect, Gaps, Trend, and Improve without assistance.
- No crashes during startup, feedback submission, diagnostics export, or clean shutdown.
- All feedback files contain category, message, timestamp, app version, and optional workspace context.
- Diagnostics zip is created successfully on every pilot machine.
- No telemetry or network upload is performed for feedback or diagnostics.

## Exit Criteria

- PASS: no blocking startup, health, shutdown, feedback, or diagnostics defects.
- PARTIAL: only minor usability issues or documentation clarifications remain.
- FAIL: any pilot user cannot launch, health check, submit feedback, export diagnostics, or close cleanly.
