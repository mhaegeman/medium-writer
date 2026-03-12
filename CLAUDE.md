# medium-writer

AI-powered Medium article generator for AI Engineering, Data Engineering, tech news, and Claude Code tutorials.

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

# Generate + publish directly to Medium as draft
medium-writer generate "Topic" --publish

# List generated articles
medium-writer list
```

## Project Structure

- `src/medium_writer/` — Core package
  - `main.py` — Typer CLI app
  - `config.py` — Settings via pydantic/dotenv
  - `researcher.py` — Topic research and ideation using Claude
  - `writer.py` — Article generation using Claude
  - `publisher.py` — Medium API integration
- `prompts/` — Jinja2 prompt templates
- `articles/` — Generated markdown articles (gitignored drafts/)

## Style Guide

- Articles should be 1200–2000 words
- Target audience: practicing engineers (not beginners)
- Use code examples where relevant
- Tone: direct, technical, opinionated

## Tech Stack

- Python 3.12+
- `anthropic` SDK — Claude API calls
- `typer` + `rich` — CLI
- `httpx` — Medium API HTTP client
- `python-dotenv` — Env config
