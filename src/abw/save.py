from __future__ import annotations

from datetime import datetime
from pathlib import Path


def _next_note_path(root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    note_root = root / "raw" / "captured_notes"
    note_root.mkdir(parents=True, exist_ok=True)
    candidate = note_root / f"{timestamp}_note.md"
    if not candidate.exists():
        return candidate
    for index in range(2, 100):
        candidate = note_root / f"{timestamp}_note_{index}.md"
        if not candidate.exists():
            return candidate
    raise RuntimeError("Could not allocate a unique captured note filename.")


def save_candidate(text: str, workspace: str | Path = ".", *, source: str = "manual_save") -> dict:
    content = str(text or "").strip()
    if not content:
        raise ValueError("No note content provided.")

    root = Path(workspace).resolve()
    note_path = _next_note_path(root)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    note_body = "\n".join(
        [
            "# Captured Note",
            "",
            "Source:",
            source,
            "",
            "Timestamp:",
            timestamp,
            "",
            "Content:",
            content,
            "",
            "Status:",
            "candidate_only",
            "",
        ]
    )
    note_path.write_text(note_body, encoding="utf-8")
    relative_path = str(note_path.relative_to(root)).replace("\\", "/")
    return {
        "path": note_path,
        "relative_path": relative_path,
        "content": note_body,
        "next_step": f"abw ingest {relative_path}",
    }
