---
description: Write the article draft from an approved outline, then self-lint
argument-hint: "<research slug>"
---

Draft the article for `research/$ARGUMENTS/` (needs `brief.md` and an approved `outline.md`).

1. Read `profile/voice.md`, `prompts/writer_system.md`, `CLAUDE.md` style rules, the brief and outline.
   Skim one or two of his published posts (`profile/medium/` or `articles/`) to calibrate rhythm.
2. Write `articles/<slug>.md` as raw Markdown for Medium: one H1, H2 sections, language-tagged
   code fences, no front matter. Cite sources inline as links, only ones in the brief's ledger.
3. Run the code you show wherever safe, so the printed output is real, not imagined.
4. Personal stories: only use what Maxime told you. Elsewhere leave `<!-- maxime: question -->`.
5. Run `medium-writer lint articles/<slug>.md`, fix everything except placeholders, repeat until clean.
6. Report word count, the remaining placeholders that need him, and the next step (`/review`).
