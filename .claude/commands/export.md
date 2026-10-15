---
description: Package a finished article for Medium (body, snippets, gists, tags, title options)
argument-hint: "<path to article, e.g. articles/my-post.md>"
---

Prepare `$ARGUMENTS` for publishing.

1. Run `medium-writer lint $ARGUMENTS --final`. Stop and report if there are errors or open
   `<!-- maxime: -->` questions.
2. Run `medium-writer export $ARGUMENTS`. Only add `--gists` if Maxime asked for gists and
   `GITHUB_TOKEN` is set: gists are created on his GitHub account and are reachable by URL.
3. Read `exports/<slug>/meta.json` and `checklist.md`, then write `exports/<slug>/publish.md` with:
   - **3 title options** (specific, human, under ~70 characters) and a recommendation
   - **Subtitle** (one sentence, promises the outcome)
   - **Tags**: confirm or improve the five suggested ones; Medium allows 5
   - **Image suggestions**: header image idea plus 1–2 diagrams worth drawing, each with alt text
   - **Seed excerpt** for Medium's preview (first 2 sentences, max 160 characters)
   - Any claim or link you could not re-verify
4. Tell him the path to `exports/<slug>/` and the remaining manual steps (paste, images, schedule).
