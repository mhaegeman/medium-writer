#!/usr/bin/env python3
"""PostToolUse hook: lint any Markdown file written or edited under articles/.

Reads the hook payload on stdin and hands the lint report back to Claude as extra context,
so style problems are fixed while drafting instead of at review time. Never blocks.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        file_path = Path(payload.get("tool_input", {}).get("file_path", "")).resolve()
    except (json.JSONDecodeError, OSError, ValueError):
        return
    articles = (ROOT / "articles").resolve()
    if file_path.suffix != ".md" or articles not in file_path.parents or not file_path.exists():
        return

    from medium_writer.lint import lint_file, word_count

    issues = lint_file(file_path)
    words = word_count(file_path.read_text(encoding="utf-8"))
    if not issues:
        report = f"mw lint {file_path.name}: {words} words, no issues."
    else:
        rows = [f"- {i.severity} L{i.line} [{i.rule}] {i.message}" for i in issues[:15]]
        report = (f"mw lint {file_path.name}: {words} words, {len(issues)} issue(s). "
                  "Fix errors now; warnings once the draft is complete.\n" + "\n".join(rows))
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                             "additionalContext": report}}))


if __name__ == "__main__":
    main()
