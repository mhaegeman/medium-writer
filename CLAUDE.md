# medium-writer

AI-powered Medium article generator targeting beginner to intermediate data engineers and data scientists. Topics: Data Engineering, AI Engineering, learning Claude Code.

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env
# Fill in your ANTHROPIC_API_KEY in .env
```

## Commands

```bash
# Generate an article on a topic
medium-writer generate "How to build a RAG pipeline with LangChain"

# Research trending topics and pick one
medium-writer research

# List generated articles
medium-writer list
```

Articles are saved to `articles/` as Markdown. Copy the file contents and paste into Medium's editor to schedule and publish.

## Project Structure

- `src/medium_writer/` — Core package
  - `main.py` — Typer CLI app
  - `config.py` — Settings via pydantic/dotenv
  - `researcher.py` — Topic research and ideation using Claude
  - `writer.py` — Article generation using Claude
- `prompts/` — Jinja2 prompt templates
- `articles/` — Generated markdown articles (gitignored drafts/)

## Style Guide

- Articles: 1000–1800 words
- Audience: beginner to intermediate data engineers / data scientists
- Tone: warm, encouraging, practical — see `tone_profile.md` (auto-filled from author's articles)
- British spelling: analyse, visualisation, labelled, behaviour
- Code examples: explain before, show output after, use realistic example data
- Always end with a call to action or invitation to engage

## Tech Stack

- Python 3.12+
- `anthropic` SDK — Claude API calls
- `typer` + `rich` — CLI
- `httpx` — resource fetching
- `python-dotenv` — Env config
