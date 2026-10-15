---
description: Sync published Medium posts and refresh the voice profile
---

1. Run `medium-writer channel sync`. If it fails (Medium blocked or offline), tell Maxime to save
   `https://medium.com/feed/@maximehaegeman` as an XML file and rerun with `--from-file <path>`;
   alternatively fetch the blog section of his portfolio (https://www.maximehaegeman.com, which
   mirrors his Medium articles) with WebFetch or `medium-writer fetch <url> --slug voice`, and
   follow its article links. He can also paste article links for you to fetch.
2. Read every post in `profile/medium/` plus `articles/` and the current `profile/voice.md`.
3. Update `profile/voice.md`: recurring phrases, analogies, structure, headings, emoji habits,
   sentence length, how code is introduced. Add 2–3 new verbatim excerpts. Keep what is still true.
4. Update the "Published so far" list and the topics he returns to in `profile/author.md`, and
   suggest adjustments to `profile/interests.yaml` keywords based on his tags and titles.
5. Show a short diff summary of what changed in his voice and interests.
