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
