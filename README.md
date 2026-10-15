# medium-writer

An LLM harness for researching and writing Medium articles in your own voice. You open a
[Claude Code](https://code.claude.com) session inside this repo, and Claude does the research,
outlining, drafting and review, following the rules in `CLAUDE.md` and the profile of the author.

Built for Maxime Haegeman ([Medium](https://medium.com/@maximehaegeman),
[GitHub](https://github.com/mhaegeman)): Data Engineering, AI Engineering and Claude Code for
beginner to intermediate data practitioners.

## Quick start

```bash
pip install -e ".[dev]"
claude            # run from the repo root
```

Then, inside the session:

```
/topics                       # what is trending in my pillars right now?
/article "Delta Lake time travel for beginners"   # research → outline → draft → review
```

No API key is needed: the Claude Code session is the model. Publishing stays manual: paste the
Markdown from `articles/` into Medium's editor, add images, schedule.

## How it works

```
/topics ──▶ /research ──▶ /outline ──▶ (you approve) ──▶ /draft ──▶ /review ──▶ articles/<slug>.md
   │            │                                            │           │
mw topics   researcher agent                               mw lint   voice-editor + fact-checker
(feeds, GitHub releases,   (official docs first,            (length, British spelling, code→output,
 Hacker News, web search)   archived with provenance)        CTA, sources, placeholders)
```

| Command | Purpose |
|---|---|
| `/topics [pillar]` | Trend detector: scans official blogs, GitHub releases, Hacker News and the web, ranks by fit |
| `/research <topic>` | Primary-source research, archived in `research/<slug>/` with a claims ledger |
| `/outline <slug>` | Outline and title options; pauses for your approval |
| `/draft <slug>` | Writes the article in your voice, running code for real output |
| `/review <path>` | Voice edit, independent fact-check, final lint |
| `/article [topic]` | The full pipeline with checkpoints |
| `/export <path>` | Medium-ready package: body, snippets (optional gists), tags, title options, checklist |
| `/series <topic>` | Plans 3–4 linked articles and adds them to `ideas.md` |
| `/repurpose <path>` | LinkedIn post variants, checked for length, hook and hashtags |
| `/voice-sync` | Pulls your published posts and refreshes the voice profile |

## Making it yours

- `profile/author.md`: who you are, built from your GitHub profile README
- `profile/voice.md`: your writing voice, learned from your articles
- `profile/interests.yaml`: topic pillars and keywords used to rank trends
- `profile/sources.yaml`: official channels to scan. Run `mw sources check` to see which work
  from your machine and prune the rest

**Teach it your channel**: `mw channel sync` downloads your latest 10 Medium posts (Medium's RSS
limit) into `profile/medium/`, then `/voice-sync` refines the voice profile from them. If Medium is
not reachable, save `https://medium.com/feed/@maximehaegeman` as a file and use `--from-file`.

## Principles

- **Primary sources first** and every claim in a ledger: official docs and release notes before blogs
- **No invented anecdotes**: personal stories come from you, or stay as `<!-- maxime: ... -->` questions
- **Deterministic guardrails** (`mw lint`) alongside the model's judgement
- **Human in the loop** at the outline and before publishing

## CLI reference

```bash
mw topics --json --days 14 --pillar claude_code
mw sources check
mw new "Working title"            # scaffolds research/<date>-<slug>/
mw fetch URL... --slug <slug>     # archives pages with provenance headers
mw channel sync
mw lint articles/x.md --final
mw export articles/x.md [--gists]  # exports/x/medium.md, snippets/, checklist.md
mw social-check linkedin.md
mw list
```

## Automation

- **Lint hook**: `.claude/hooks/lint_article.py` runs after every write or edit of `articles/*.md` and
  feeds the lint report back to Claude, so problems get fixed while drafting.
- **CI** (`ci.yml`): ruff, pytest and `mw lint` on every article for each PR.
- **Weekly topics** (`weekly-topics.yml`): every Monday a GitHub issue lists the top trending topics
  for your pillars (`mw topics --markdown`). Also runnable by hand from the Actions tab.

## Development

```bash
python -m pytest
ruff check .
```

`prompts/writer_system.md` also powers the static prompt-builder UI in `docs/` (GitHub Pages).
