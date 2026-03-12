# medium-writer

AI-powered Medium article writer for beginner and intermediate data engineers and data scientists. Powered by Claude.

Pick a topic, drop in some resources, and get a full draft written in your voice.

## Features

- **Topic suggestions** — browse curated ideas across Data Engineering, AI Engineering, and Claude tooling
- **Resource-aware writing** — pass URLs or local files and the article will incorporate them
- **Your tone** — fill in `tone_profile.md` once and every article will sound like you
- **Streaming output** — watch the article write itself in your terminal
- **Medium publishing** — publish directly as draft, public, or unlisted

## Setup

```bash
# Install
pip install -e .

# Configure
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

Get an Anthropic API key at [console.anthropic.com](https://console.anthropic.com).

## Usage

### Research topics

```bash
medium-writer research
medium-writer research "Data Engineering"
```

Browse AI-suggested topics, then pick one to generate immediately.

### Generate an article

```bash
# Basic
medium-writer generate "What is dbt and why should I care?"

# With resources (URLs or local files)
medium-writer generate "Building your first data pipeline" \
  --resources "https://docs.prefect.io/latest/,./my_notes.md"

# Generate and publish to Medium as draft
medium-writer generate "My topic" --publish --tags "data engineering,python"
```

### Publish an existing article

```bash
medium-writer publish articles/2026-03-01-my-article.md --status public
```

### List generated articles

```bash
medium-writer list
```

## Personalising the output

Fill in `tone_profile.md` with your writing style. The more detail you add, the better the match. A sample excerpt of your own writing has the strongest effect.

```
# My Writing Tone Profile

## My Style in One Sentence
I explain things like I'm talking to a smart friend who just started in data.

## Sample Excerpt
[paste a paragraph of your own writing here]
```

## Cost & Performance

Research uses `claude-haiku-4-5` (fast and cheap). Writing uses `claude-sonnet-4-6` by default.

Both use **prompt caching** on system prompts and resource blocks, so repeat runs on the same topic cost significantly less. Rate limits are handled automatically with exponential backoff.

To override the model:
```bash
# In .env
CLAUDE_MODEL=claude-opus-4-6
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
| `MEDIUM_INTEGRATION_TOKEN` | No | For publishing to Medium |
| `MEDIUM_PUBLISH_STATUS` | No | `draft` (default), `public`, `unlisted` |
| `CLAUDE_MODEL` | No | Model for writing (default: `claude-sonnet-4-6`) |
| `ARTICLES_DIR` | No | Output directory (default: `articles/`) |
