"""CLI entry point for medium-writer."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="medium-writer",
    help="AI-powered Medium article writer using Claude.",
    add_completion=False,
)
console = Console()


@app.command()
def generate(
    topic: str = typer.Argument(..., help="Article topic or title"),
    resources: Optional[str] = typer.Option(
        None,
        "--resources",
        "-r",
        help="Comma-separated URLs or file paths to incorporate (e.g. 'https://docs.example.com,./notes.md')",
    ),
    publish: bool = typer.Option(False, "--publish", "-p", help="Publish to Medium after generation"),
    status: str = typer.Option("draft", "--status", "-s", help="Medium publish status: draft, public, unlisted"),
    no_stream: bool = typer.Option(False, "--no-stream", help="Disable streaming output"),
    tags: str = typer.Option("", "--tags", "-t", help="Comma-separated tags (max 5)"),
):
    """Generate a Medium article on the given topic.

    Examples:

        medium-writer generate "What is dbt and why should I care?"

        medium-writer generate "Building a RAG pipeline" --resources "https://docs.llamaindex.ai/..."

        medium-writer generate "My topic" --publish --tags "data engineering,python"
    """
    from .researcher import research_topic
    from .writer import generate_article

    resource_list = [r.strip() for r in resources.split(",") if r.strip()] if resources else None

    console.print(Panel(f"[bold cyan]Researching:[/bold cyan] {topic}", expand=False))
    try:
        brief = research_topic(topic)
    except Exception as e:
        console.print(f"[red]Research failed:[/red] {e}")
        raise typer.Exit(1)

    if resource_list:
        console.print(f"[dim]Resources to incorporate:[/dim] {', '.join(resource_list)}")

    console.print(Panel("[bold cyan]Writing article...[/bold cyan]", expand=False))
    try:
        article_md, output_path = generate_article(
            topic=topic,
            research_brief=brief,
            resources=resource_list,
            stream=not no_stream,
        )
    except Exception as e:
        console.print(f"[red]Writing failed:[/red] {e}")
        raise typer.Exit(1)

    console.print(f"\n[green]Saved:[/green] {output_path}")

    if publish:
        _publish_article(topic, article_md, tags, status)


@app.command()
def research(
    category: str = typer.Argument(
        "",
        help="Category to focus on (e.g. 'Data Engineering', 'AI Engineering')",
    ),
    generate_after: bool = typer.Option(
        True,
        "--generate/--no-generate",
        help="Prompt to generate an article after showing topics",
    ),
):
    """Browse topic ideas and optionally generate an article.

    Examples:

        medium-writer research

        medium-writer research "Data Engineering"

        medium-writer research --no-generate
    """
    from .researcher import suggest_topics

    console.print(Panel("[bold cyan]Fetching topic ideas...[/bold cyan]", expand=False))
    try:
        topics = suggest_topics(category or None)
    except Exception as e:
        console.print(f"[red]Research failed:[/red] {e}")
        raise typer.Exit(1)

    table = Table(title="Suggested Topics", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="bold", min_width=30)
    table.add_column("Category", style="cyan", min_width=20)
    table.add_column("Why now?")

    for i, t in enumerate(topics, 1):
        table.add_row(str(i), t.get("title", ""), t.get("category", ""), t.get("why_now", ""))

    console.print(table)

    if not generate_after:
        return

    choice = typer.prompt(
        "\nEnter a number to generate that article (or press Enter to skip)",
        default="",
    )
    if not choice.strip().isdigit():
        return

    idx = int(choice.strip()) - 1
    if not (0 <= idx < len(topics)):
        console.print("[yellow]Invalid selection.[/yellow]")
        return

    selected = topics[idx]
    resources_input = typer.prompt(
        "Paste resource URLs (comma-separated) or press Enter to skip",
        default="",
    )
    resource_list = [r.strip() for r in resources_input.split(",") if r.strip()] or None

    console.print("")
    from .researcher import research_topic
    from .writer import generate_article

    console.print(Panel(f"[bold cyan]Researching:[/bold cyan] {selected['title']}", expand=False))
    brief = research_topic(selected["title"])

    console.print(Panel("[bold cyan]Writing article...[/bold cyan]", expand=False))
    article_md, output_path = generate_article(
        topic=selected["title"],
        research_brief=brief,
        resources=resource_list,
        stream=True,
    )
    console.print(f"\n[green]Saved:[/green] {output_path}")


@app.command(name="list")
def list_articles():
    """List all generated articles."""
    from .config import config

    articles = sorted(config.articles_dir.glob("*.md"), reverse=True)
    if not articles:
        console.print("[yellow]No articles found in:[/yellow]", config.articles_dir)
        return

    table = Table(title=f"Articles in {config.articles_dir}/", show_lines=True)
    table.add_column("File", style="cyan")
    table.add_column("Size", justify="right")

    for path in articles:
        size_kb = path.stat().st_size / 1024
        table.add_row(path.name, f"{size_kb:.1f} KB")

    console.print(table)


@app.command()
def publish(
    file: Path = typer.Argument(..., help="Path to a generated markdown article"),
    title: str = typer.Option("", "--title", help="Override article title"),
    status: str = typer.Option("draft", "--status", "-s", help="draft, public, or unlisted"),
    tags: str = typer.Option("", "--tags", "-t", help="Comma-separated tags (max 5)"),
):
    """Publish an existing markdown article to Medium."""
    if not file.exists():
        console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(1)

    content = file.read_text(encoding="utf-8")
    article_title = title or file.stem.replace("-", " ").title()
    _publish_article(article_title, content, tags, status)


def _publish_article(topic: str, article_md: str, tags: str, status: str) -> None:
    from .publisher import MediumPublisher

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    console.print(Panel("[bold cyan]Publishing to Medium...[/bold cyan]", expand=False))
    try:
        publisher = MediumPublisher()
        result = publisher.publish(
            title=topic,
            content_markdown=article_md,
            tags=tag_list or None,
            status=status,
        )
        console.print(f"[green]Published![/green] URL: {result.get('url', 'unknown')}")
    except Exception as e:
        console.print(f"[red]Publish failed:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
