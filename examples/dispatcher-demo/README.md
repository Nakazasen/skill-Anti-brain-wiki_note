# Dispatcher + Executor Demo

This example demonstrates how the `/abw-ask` system handles the **Dispatcher + Executor** lane for code fixes.

## How to test

1. Ensure `.brain/resume_state.json` exists (required by Guard A).
2. Run the following input through `/abw-ask`:
   > "sửa lỗi typo trong file examples/dispatcher-demo/demo_bug.py"
3. The system should:
   - Identify the intent as `execution`.
   - Pass the safety guards.
   - Dispatch to the `/code` lane.
   - Execute the fix and run a follow-up `/abw-eval`.

## Files
- `demo_bug.py`: A simple script used to verify that code changes are correctly applied and evaluated.
