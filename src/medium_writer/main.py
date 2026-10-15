"""CLI helpers for the medium-writer harness.

The thinking is done by Claude inside a Claude Code session (see CLAUDE.md and
.claude/commands/). This CLI provides the deterministic tools it calls: scanning
sources, archiving research, syncing your Medium channel and linting drafts.
"""

import json
import re
from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import config

app = typer.Typer(
    name="medium-writer",
    help="Research and writing harness for blog articles. Run it from a Claude Code session.",
    add_completion=False,
    no_args_is_help=True,
)
sources_app = typer.Typer(help="Inspect the configured source list.", no_args_is_help=True)
channel_app = typer.Typer(help="Sync your published Medium posts.", no_args_is_help=True)
app.add_typer(sources_app, name="sources")
app.add_typer(channel_app, name="channel")
console = Console()


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


@app.command()
def topics(
    days: int = typer.Option(14, help="Only consider items newer than this many days."),
    limit: int = typer.Option(15, help="Maximum topics to show."),
    pillar: str = typer.Option(None, help="Restrict to one pillar from profile/interests.yaml."),
    refresh: bool = typer.Option(False, "--refresh", help="Ignore the 1h feed cache."),
    as_json: bool = typer.Option(False, "--json", help="Machine-readable output for Claude."),
):
    """Scan official channels and communities, ranked by fit with your interests."""
    from .sources import scan
    from .trends import rank

    result = scan(refresh=refresh)
    ranked = rank(result.items, days=days, pillar=pillar)[:limit]
    failed = [r for r in result.reports if not r.ok]

    if as_json:
        payload = {
            "ranked": [
                {
                    "score": r.score,
                    "title": r.item.title,
                    "url": r.item.url,
                    "source": r.item.source,
                    "kind": r.item.kind,
                    "published": r.item.published.date().isoformat() if r.item.published else None,
                    "points": r.item.points,
                    "pillars": r.pillars,
                    "matched": r.matched,
                    "already_covered_by": r.covered_by or None,
                    "summary": r.item.summary,
                }
                for r in ranked
            ],
            "sources_ok": sum(r.ok for r in result.reports),
            "sources_failed": [{"name": r.name, "error": r.error} for r in failed],
        }
        typer.echo(json.dumps(payload, indent=2))
        return

    table = Table(title=f"Trending for you (last {days} days)", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Score", width=6)
    table.add_column("Title", style="bold", min_width=34)
    table.add_column("Source", style="cyan")
    table.add_column("Pillars")
    for i, r in enumerate(ranked, 1):
        title = r.item.title + (f"\n[yellow]covered: {r.covered_by}[/yellow]" if r.covered_by else "")
        table.add_row(str(i), str(r.score), f"{title}\n[dim]{r.item.url}[/dim]", r.item.source,
                      ", ".join(r.pillars))
    console.print(table)
    ok = sum(r.ok for r in result.reports)
    console.print(f"[dim]{ok}/{len(result.reports)} sources reachable.[/dim]")
    if failed:
        console.print("[yellow]Unreachable:[/yellow] " + ", ".join(r.name for r in failed))


@sources_app.command("check")
def sources_check():
    """Ping every configured source and report which ones work from this machine."""
    from .sources import scan

    result = scan(refresh=True)
    table = Table(title="Source health")
    table.add_column("Source")
    table.add_column("Status")
    table.add_column("Items", justify="right")
    table.add_column("Detail", style="dim")
    for r in result.reports:
        table.add_row(r.name, "[green]ok[/green]" if r.ok else "[red]fail[/red]",
                      str(r.count), r.error)
    console.print(table)


@sources_app.command("list")
def sources_list():
    """Show the configured sources."""
    from .sources import load_sources

    cfg = load_sources()
    for f in cfg.get("feeds", []):
        console.print(f"[cyan]{f['name']}[/cyan] {f['url']}")
    for g in cfg.get("github_releases", []):
        console.print(f"[cyan]{g['repo']}[/cyan] (GitHub releases)")
    if cfg.get("hackernews"):
        console.print("[cyan]Hacker News[/cyan] front page + keyword queries")


@app.command()
def fetch(
    urls: list[str] = typer.Argument(..., help="URLs or local files to read."),
    slug: str = typer.Option(None, "--slug", "-s", help="Archive into research/<slug>/sources/."),
    max_chars: int = typer.Option(20000, help="Truncate each page to this many characters."),
):
    """Fetch pages as clean text. With --slug, archive them with provenance headers."""
    from .fetch import archive_page, fetch_page

    dest = config.RESEARCH_DIR / slug / "sources" if slug else None
    existing = len(list(dest.glob("*.md"))) if dest and dest.exists() else 0
    for i, u in enumerate(urls, existing + 1):
        try:
            page = fetch_page(u, max_chars=max_chars)
        except Exception as e:
            console.print(f"[red]FAILED[/red] {u}: {e}")
            continue
        if dest:
            path = archive_page(page, dest, i)
            console.print(f"[green]saved[/green] {path.relative_to(config.ROOT)} ({len(page.text)} chars)")
        else:
            typer.echo(f"=== {page.source}\n# {page.title}\n\n{page.text}\n")


@app.command()
def new(title: str = typer.Argument(..., help="Working title of the article.")):
    """Scaffold research/<date>-<slug>/ with a brief template."""
    slug = f"{date.today().isoformat()}-{_slugify(title)}"
    folder = config.RESEARCH_DIR / slug
    (folder / "sources").mkdir(parents=True, exist_ok=True)
    brief = folder / "brief.md"
    if not brief.exists():
        template = (config.ROOT / "prompts" / "brief_template.md").read_text(encoding="utf-8")
        brief.write_text(template.replace("{{title}}", title).replace("{{slug}}", slug),
                         encoding="utf-8")
    typer.echo(slug)


@app.command()
def lint(
    path: Path = typer.Argument(..., help="Markdown draft to check."),
    final: bool = typer.Option(False, "--final", help="Treat leftover placeholders as errors."),
    as_json: bool = typer.Option(False, "--json"),
):
    """Check a draft against the style guide (length, spelling, structure, CTA, sources)."""
    from .lint import lint_file, word_count

    issues = lint_file(path, final=final)
    words = word_count(path.read_text(encoding="utf-8"))
    if as_json:
        typer.echo(json.dumps({"words": words, "issues": [i.__dict__ for i in issues]}, indent=2))
    else:
        console.print(f"[bold]{path}[/bold]: {words} words")
        for i in issues:
            colour = "red" if i.severity == "error" else "yellow"
            console.print(f"  [{colour}]{i.severity:5}[/{colour}] L{i.line:<4} {i.rule:12} {i.message}")
        if not issues:
            console.print("  [green]No issues.[/green]")
    if any(i.severity == "error" for i in issues):
        raise typer.Exit(1)


@app.command("list")
def list_articles():
    """List articles in articles/ with word counts and lint status."""
    from .lint import lint_file, word_count

    table = Table(title="Articles")
    table.add_column("File")
    table.add_column("Title", style="bold")
    table.add_column("Words", justify="right")
    table.add_column("Lint")
    for path in sorted(config.ARTICLES_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = next((ln[2:] for ln in text.splitlines() if ln.startswith("# ")), "(untitled)")
        issues = lint_file(path)
        errs = sum(i.severity == "error" for i in issues)
        warns = len(issues) - errs
        table.add_row(path.name, title, str(word_count(text)), f"{errs} errors, {warns} warnings")
    console.print(table)


@channel_app.command("sync")
def channel_sync(
    handle: str = typer.Option(config.MEDIUM_HANDLE, help="Medium handle, without the @."),
    from_file: str = typer.Option(None, "--from-file", help="Read a saved RSS XML instead."),
):
    """Download your latest Medium posts (RSS returns the 10 most recent) into profile/medium/."""
    from .channel import sync

    try:
        posts = sync(handle, from_file)
    except Exception as e:
        console.print(f"[red]Sync failed:[/red] {e}")
        console.print("Tip: save https://medium.com/feed/@%s in a browser and use --from-file." % handle)
        raise typer.Exit(1)
    for p in posts:
        console.print(f"[green]synced[/green] {p['date']} {p['title']}")
    console.print(f"[dim]{len(posts)} posts written to profile/medium/[/dim]")


if __name__ == "__main__":
    app()
