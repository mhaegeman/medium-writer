---
description: Turn a finished article into a LinkedIn post (and optional thread of hooks)
argument-hint: "<path to article, e.g. articles/my-post.md>"
---

Repurpose `$ARGUMENTS` for LinkedIn.

1. Read the article, `profile/voice.md` and `profile/author.md`. LinkedIn is tighter than Medium:
   same warmth and British spelling, shorter sentences, more white space, no headings.
2. Write `exports/<slug>/linkedin.md` with **two variants** of one post:
   - **A (lesson)**: hook line of ≤200 characters that states the problem or a surprising claim,
     3–5 short paragraphs delivering one takeaway, one tiny code or command example only if it fits,
     a closing question that invites replies, 3 hashtags at most.
   - **B (story)**: same takeaway told through the "What I got wrong" angle. Use only
     experiences Maxime has confirmed; otherwise leave `<!-- maxime: question -->`.
   Put the Medium link in a line marked `First comment:` rather than the body.
3. Run `medium-writer social-check exports/<slug>/linkedin.md` on each variant (paste each into
   its own temporary file under the scratchpad if needed) and fix every error and warning.
4. Suggest a posting time window for a Copenhagen-based audience and a one-line follow-up comment
   to post an hour later. Do not publish anything.
