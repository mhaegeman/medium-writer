---
description: Detect trending topics worth writing about and rank them for Maxime
argument-hint: "[pillar or keyword, optional]"
---

Find article ideas for Maxime's Medium channel. Focus: $ARGUMENTS (if empty, all pillars).

1. Read `profile/author.md`, `profile/interests.yaml` and `ideas.md` (backlog, may not exist).
2. Run `medium-writer topics --json --days 14` (add `--pillar <name>` if a pillar was given).
   Note any `sources_failed`; mention them briefly but carry on.
3. Run 3–5 WebSearch queries for what is new in the last two weeks in his pillars (official
   announcements, new releases, notable launches). Prefer vendor and official domains.
4. Combine the scan with the web results. Drop anything in `already_covered_by`, anything too
   advanced for beginner/intermediate readers, and pure paper summaries.
5. Present the **top 5** as a table: working title, angle (one sentence), why now (with link to
   the primary source), pillar, difficulty for the reader, and a "fit for Maxime" note linking to
   one of his real projects or skills where honest.
6. Ask which to pursue. When he picks one, append it to `ideas.md` and offer to start `/research`.
