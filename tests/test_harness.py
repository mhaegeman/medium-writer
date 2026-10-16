from datetime import UTC, datetime, timedelta

from typer.testing import CliRunner

from medium_writer import channel, fetch, lint, sources, trends
from medium_writer.main import app

RSS = """<?xml version="1.0"?><rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel><item><title>Claude Code adds hooks</title><link>https://ex.com/a?utm=1</link>
<pubDate>{date}</pubDate><description>New hooks for Claude Code and MCP</description>
<category>claude-code</category>
<content:encoded><![CDATA[<h1>Hi</h1><p>Hello <b>world</b></p><script>x()</script>]]></content:encoded>
</item></channel></rss>"""

ATOM = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>v1.2</title>
<link rel="alternate" href="https://github.com/o/r/releases/tag/v1.2"/>
<updated>2026-10-10T10:00:00Z</updated></entry></feed>"""


def _rfc822(dt: datetime) -> str:
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def test_parse_rss_and_atom():
    now = datetime.now(UTC)
    items = sources.parse_feed(RSS.format(date=_rfc822(now)), source="T")
    assert items[0].title == "Claude Code adds hooks" and items[0].published
    atom = sources.parse_feed(ATOM, source="A", kind="release")
    assert atom[0].url.endswith("v1.2") and atom[0].published.year == 2026


def test_rank_prefers_fresh_official_and_filters():
    now = datetime.now(UTC)
    fresh = sources.Item("Claude Code hooks explained", "https://a", "Anthropic", trust=2,
                         published=now - timedelta(days=1))
    stale = sources.Item("Claude Code hooks explained again", "https://b", "Blog", trust=1,
                         published=now - timedelta(days=13))
    spam = sources.Item("Crypto webinar on Spark", "https://c", "X", published=now)
    off = sources.Item("Gardening tips", "https://d", "X", published=now)
    old = sources.Item("Airflow news", "https://e", "X", published=now - timedelta(days=60))
    ranked = trends.rank([stale, fresh, spam, off, old], days=14)
    assert [r.item.url for r in ranked] == ["https://a", "https://b"]
    assert "claude_code" in ranked[0].pillars


def test_html_to_text_strips_scripts():
    title, text = fetch.html_to_text(
        "<html><title>T</title><body><script>bad()</script><h2>Head</h2><p>Body</p></body></html>"
    )
    assert title == "T" and "bad()" not in text and "## Head" in text


def test_channel_parse_posts():
    posts = channel.parse_posts(RSS.format(date=_rfc822(datetime.now(UTC))))
    assert posts[0]["url"] == "https://ex.com/a" and "Hello world" in posts[0]["body"]
    assert posts[0]["tags"] == ["claude-code"]


GOOD = (
    "# A Title\n\nWhy does my pipeline fail? Here is the story.\n\n"
    + "".join(f"## Section {i}\n\n" + "Short clear sentence about data. " * 40 + "\n\n"
               for i in range(5))
    + "See [docs](https://a.com) and [more](https://b.com).\n\n"
    "```python\nprint(1)\n```\n\nThe output is 1.\n\n"
    "Try it today and let me know how it goes in the comments!\n"
)


def test_lint_good_draft_is_clean():
    issues = lint.lint(GOOD)
    assert [i for i in issues if i.severity == "error"] == []
    assert not any(i.rule in ("spelling", "cta", "code", "sources") for i in issues)


def test_lint_flags_problems():
    bad = ("# One\n\n# Two\n\nIn this article we analyze color.\n\n```python\nx = 1\n```\n\n"
           "TODO fix\n")
    rules = {i.rule for i in lint.lint(bad, final=True)}
    assert {"title", "length", "spelling", "hook", "code", "sources", "cta", "placeholder"} <= rules


def test_lint_ignores_code_and_headings_in_fences():
    md = "# T\n\n```python\n# comment\ncolor = 1\n```\n"
    issues = lint.lint(md)
    assert not any(i.rule == "title" for i in issues)
    assert not any(i.rule == "spelling" for i in issues)


def test_cli_lint_exit_code(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("# One\n\n# Two\n")
    res = CliRunner().invoke(app, ["lint", str(f)])
    assert res.exit_code == 1


def test_export_package(tmp_path, monkeypatch):
    from medium_writer import export

    monkeypatch.setattr(export, "EXPORTS_DIR", tmp_path / "exports")
    art = tmp_path / "post.md"
    art.write_text(GOOD + "\n```sql\nSELECT 1;\n```\n\nThe query returns 1 on Airflow and dbt. Let me know!\n")
    dest = export.export_article(art)
    body = (dest / "medium.md").read_text()
    assert not body.startswith("# A Title") and "```python" in body
    assert (dest / "snippets" / "snippet-01.py").read_text().strip() == "print(1)"
    assert (dest / "snippets" / "snippet-02.sql").exists()
    meta = __import__("json").loads((dest / "meta.json").read_text())
    assert meta["title"] == "A Title" and meta["snippets"] == 2 and meta["tags"]
    assert (dest / "checklist.md").exists()


def test_export_blocked_by_lint_errors(tmp_path, monkeypatch):
    import pytest

    from medium_writer import export

    monkeypatch.setattr(export, "EXPORTS_DIR", tmp_path / "exports")
    art = tmp_path / "bad.md"
    art.write_text("# One\n\n# Two\n\nTODO\n")
    with pytest.raises(ValueError):
        export.export_article(art)
    export.export_article(art, force=True)


def test_replace_snippets_with_gist_urls():
    from medium_writer import export

    body = "Intro\n\n```python\na=1\n```\n\nMid\n\n```sql\nSELECT 1\n```\n"
    out = export.replace_snippets(body, {1: "https://gist.github.com/x/1"})
    assert "https://gist.github.com/x/1" in out and "SELECT 1" in out and "a=1" not in out


def test_linkedin_checks():
    from medium_writer.social import check_linkedin

    assert check_linkedin("Hook?\n\nBody. What do you think?\n\n#a #b") == []
    msgs = " ".join(i.message for i in check_linkedin("x" * 3100 + " color"))
    assert "3000" in msgs and "closing question" in msgs and "American" in msgs


def test_lint_hook_reports_and_ignores_other_files(tmp_path):
    import json
    import subprocess
    import sys

    from medium_writer.config import ROOT

    hook = ROOT / ".claude" / "hooks" / "lint_article.py"
    art = ROOT / "articles" / "_hook_test.md"
    art.write_text("# T\n\nIn this article we analyze things.\n")
    try:
        out = subprocess.run([sys.executable, str(hook)], capture_output=True, text=True,
                             input=json.dumps({"tool_input": {"file_path": str(art)}})).stdout
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        assert "spelling" in ctx and "_hook_test.md" in ctx
        other = subprocess.run([sys.executable, str(hook)], capture_output=True, text=True,
                               input=json.dumps({"tool_input": {"file_path": "README.md"}})).stdout
        assert other == ""
    finally:
        art.unlink()


def test_topics_markdown_cli(monkeypatch):
    from medium_writer import sources

    now = datetime.now(UTC)
    item = sources.Item("Claude Code hooks", "https://a", "Anthropic", trust=2, published=now)
    monkeypatch.setattr(sources, "scan", lambda refresh=False: sources.Scan(
        [item], [sources.SourceReport("Anthropic", True, 1)]))
    res = CliRunner().invoke(app, ["topics", "--markdown"])
    assert res.exit_code == 0 and "- [ ] **[Claude Code hooks](https://a)**" in res.output


def test_rank_keeps_one_release_per_source():
    now = datetime.now(UTC)
    items = [sources.Item(f"Anthropic SDK: 1.{i}.0", f"https://p/{i}", "PyPI Anthropic",
                          kind="release", trust=2, published=now - timedelta(days=i))
             for i in range(5)]
    assert len(trends.rank(items, days=14)) == 1
