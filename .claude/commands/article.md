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
5. **Package**: follow `/export` (title options, subtitle, tags, images, gists on request).
6. **Handover**: print the path to `exports/<slug>/`, remaining questions and manual steps (paste
   into Medium, add images, schedule). Offer `/repurpose` for LinkedIn. Mark the idea as written
   in `ideas.md`.

Never skip the approval pause after the outline. Keep each stage's output brief.
