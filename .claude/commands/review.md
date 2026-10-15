---
description: Voice edit and fact-check a draft, then lint it
argument-hint: "<path to article, e.g. articles/my-draft.md>"
---

Review `$ARGUMENTS`.

1. Run the `voice-editor` subagent on the draft and wait for it.
2. Then run the `fact-checker` subagent on the edited draft.
3. Apply every fix it marks `wrong`; for `unverifiable`, find a source or soften/remove the claim.
4. Run `medium-writer lint $ARGUMENTS --final`.
5. Output a short verdict: ready / needs Maxime's input (list the `<!-- maxime: -->` questions) /
   needs rewrite. Include the final word count and the title options for him to choose from.
