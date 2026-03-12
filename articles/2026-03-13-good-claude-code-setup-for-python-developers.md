# Good Claude Code Setup for Python Developers

If you've ever pasted 200 lines of a messy pipeline into a chat window and watched Claude lose track of the context halfway through, you already know the frustration. Text chat is great for questions. It's not really built for "please help me understand why this DAG is failing across three interconnected files." That's where Claude Code comes in — and where most people give up too early because their setup is fighting them.

This isn't a features tour. It's the setup guide I wish I'd had when I first started using Claude Code for actual data engineering work.

## Claude Code vs. Text Chat: Knowing Which Tool to Reach For

Think of Claude Code as a colleague who can sit down at your laptop and navigate your whole project — not just the snippet you copied into Slack. Text chat is more like a phone call: great for quick questions, bad for "let me walk you through the whole thing."

You want Claude Code when you're doing multi-file refactoring (splitting a 400-line pipeline into proper modules), debugging something that spans task code *and* logs, or adding type hints across an entire package. You probably don't need it when you're just asking how `groupby` works in Pandas or exploring a concept you've never seen before. In those cases, the chat interface is faster and lighter. Claude Code shines when your problem has *context spread across files* — that's its real superpower.

A good rule of thumb: if your question requires you to share more than one file to explain it properly, reach for Claude Code.

## Preparing Your Workspace Before You Start

Here's something counterintuitive: Claude Code works best when your codebase is already reasonably clean. That's not a bug — it's useful pressure. If Claude Code is struggling to understand your project, chances are a new teammate would too.

That said, a few small habits make a big difference. Start with your README. Claude Code reads it, and a README that explains what the project does, what the entrypoints are, and how the data flows through the system will help it give you much better suggestions. You don't need a novel — three paragraphs and a quick directory overview is plenty.

Folder structure matters more than you'd think. For data projects, a clear separation between `src/`, `tests/`, `data/`, and `notebooks/` gives Claude Code a map. When everything lives in a flat list of files at the root level, it has to guess at the intent. When you have this:

```
my_pipeline/
├── src/
│   ├── ingest.py
│   ├── transform.py
│   └── data_validation.py
├── tests/
│   ├── test_ingest.py
│   └── test_transform.py
├── data/
│   └── raw/
├── notebooks/
│   └── exploration.ipynb
├── pyproject.toml
└── README.md
```

...it can navigate with confidence.

One more thing: your `.gitignore` is not just for Git. Claude Code respects it. If a credentials file or a `.env` with database passwords is accidentally tracked by version control, Claude Code can read it. This is a good moment to audit your repo — make sure secrets are excluded before you start working with any AI tool that has file access. 🔒

## Python-Specific Setup That Actually Helps

A few Python-specific files do a lot of heavy lifting here. If you're using `pyproject.toml`, Claude Code can read your dependencies, your build configuration, and your tool settings all in one place. If you're still on a plain `requirements.txt`, that's fine too — but make sure it's up to date and split logically (some projects keep `requirements.txt` for production and `requirements-dev.txt` for linting, testing tools, etc.). Claude Code will use these to understand what libraries are available to you.

Include a `.python-version` file (if you use `pyenv`) or a `[tool.python]` section in your `pyproject.toml`. Knowing which Python version you're on helps Claude Code avoid suggesting syntax or APIs that won't work in your environment.

For formatting, if you use Black and isort, add their configs:

```toml
# pyproject.toml
[tool.black]
line-length = 88
target-version = ["py311"]

[tool.isort]
profile = "black"
```

Claude Code will respect these when it rewrites or generates code for you. Without them, it'll make reasonable guesses — but "reasonable guesses" and "passing your CI checks" aren't always the same thing. 😉

One important caveat: Claude Code edits files, but it does not run them. It won't execute your pipeline and tell you the output. You still need to run tests locally and verify the results yourself. This trips up a lot of people early on. Think of it as a very capable pair programmer who writes the code with you, but doesn't touch the keyboard when it's time to hit Run.

## Managing Context Without Hitting the Wall

Token limits are real, and on large projects, they bite. If you open Claude Code and immediately say "refactor my entire data pipeline," you're going to run into trouble — either it'll miss files, or it'll lose coherence halfway through a big change.

The better approach is to scope your requests into phases. Let's say you have a single 400-line transformation script that does ingestion, cleaning, and output all in one place. Rather than asking Claude Code to "fix all of it," try this sequence:

**Phase 1** — Ask it to read the file and summarise what each section is doing. This is cheap on tokens and tells you whether it has understood the structure correctly.

**Phase 2** — Ask it to split the file into three focused modules: `ingest.py`, `transform.py`, and `load.py`. One task, clear scope.

**Phase 3** — Once that's done, ask it to generate unit tests for `transform.py` specifically.

Each phase is self-contained. You can verify the output before moving on. This is also how experienced Claude Code users work — not as one giant instruction, but as a structured conversation with checkpoints.

File naming also affects how well Claude Code navigates your project. `utils.py` is almost meaningless — it could contain anything. `data_validation.py`, `schema_checks.py`, `pipeline_helpers.py` — these names carry intent. Claude Code uses filenames as part of its understanding of your codebase. Small naming choices add up. 🤓

## A Real Workflow: Debugging a Failing Airflow DAG

Let me make this concrete. Imagine you have an Airflow DAG that's failing intermittently, and the error is somewhere between the task definition and the scheduler logs. Here's how to structure the request for Claude Code to actually help you.

First, include the relevant files — the DAG definition, the task functions it calls, and a snippet of the actual error logs. Don't paste the entire log file; trim it to the last 50 lines where the failure occurred.

A prompt that works well looks like this:

```
Here are three files:
1. dags/customer_sync_dag.py — the DAG definition
2. src/customer_sync.py — the task functions it calls
3. logs/customer_sync_error.txt — the last failure log (trimmed to 60 lines)

The DAG fails on the `transform_records` task. It succeeds on the first two runs 
of the day, then fails on the third. Please read all three files and identify 
the likely cause. Do not make any changes yet — just explain what you find.
```

Notice a few things here. We're asking it to *read and explain* before touching anything. We've given it the log but trimmed it to what's relevant. And we've named the specific failing task so it knows where to focus. This structure gets you a much sharper diagnosis than "my DAG is broken, can you help?"

For notebooks: Claude Code can read `.ipynb` files, but if you need to refactor exploration code into production logic, ask it to write the result as a `.py` file. Refactoring directly inside notebooks is messier and harder to version. 

## What I Got Wrong at First

Honestly, my first week with Claude Code was underwhelming — because I was treating it like a smarter chat window. I'd paste one file, ask a vague question, and get a generic answer.

The shift happened when I started preparing my workspace *before* starting a session. A clean README, a proper folder structure, a `pyproject.toml` with my tooling config — these aren't just good practices in general, they're how you give Claude Code the context it needs to be genuinely useful.

I also underestimated how much file naming mattered. I had a `helpers.py` that was doing three completely different things. Claude Code kept misunderstanding what I wanted changed because the file itself was incoherent. Renaming it and splitting it into two focused files immediately improved the quality of suggestions. That felt like a small lesson in how our tools reflect our habits back at us. 🫶

## Start Small, Then Scale Up

The one thing to take away from all of this: a good Claude Code session starts before you open the tool. Structure your repo clearly, name your files meaningfully, keep your `pyproject.toml` honest, and trim your context to what's actually relevant. Do those things, and you'll stop feeling like you're fighting the tool and start feeling like you have a capable collaborator alongside you.

So why wait? Pick one messy script in your current project — ideally one that's grown too big to reason about easily — and try the phased approach described above. Read first, refactor second, test third. See how far you get. If you have questions along the way, feel free to share what you're working on in the comments — I'd love to hear how it goes! 🙌