---
description: End-to-end article: topic, research, outline, draft, review (pauses for approval)
argument-hint: "[topic, or leave empty to detect trending topics]"
---

Run the whole pipeline for: $ARGUMENTS

If no topic was given, run `/topics` first and let Maxime choose. Then proceed in stages, using the
commands' instructions exactly:

1. **Research**: follow `/research` (scaffold, researcher subagent, personal-angle questions).
2. **Outline**: follow `/outline`. **Stop and wait for his approval** or edits.
3. **Draft**: follow `/draft`.
4. **Review**: follow `/review`.
5. **Handover**: print the path to `articles/<slug>.md`, remaining questions, 3 title options and
   suggested Medium tags (max 5). Remind him to paste the Markdown into Medium, add images and
   schedule it. Mark the idea as written in `ideas.md`.

Never skip the approval pause after the outline. Keep each stage's output brief.
