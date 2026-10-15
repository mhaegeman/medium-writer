"""Deterministic style checks for a draft, mirroring the rules in profile/voice.md."""

import re
from dataclasses import dataclass
from pathlib import Path

MIN_WORDS, MAX_WORDS = 1000, 1800

# American -> British. Checked against prose only (code, inline code and URLs are stripped).
US_TO_UK = {
    "analyze": "analyse", "analyzed": "analysed", "analyzing": "analysing",
    "visualization": "visualisation", "visualizations": "visualisations",
    "visualize": "visualise", "visualizing": "visualising",
    "behavior": "behaviour", "behaviors": "behaviours",
    "color": "colour", "colors": "colours", "colorful": "colourful",
    "labeled": "labelled", "labeling": "labelling",
    "organize": "organise", "organized": "organised", "organization": "organisation",
    "optimize": "optimise", "optimized": "optimised", "optimization": "optimisation",
    "normalize": "normalise", "normalized": "normalised", "normalization": "normalisation",
    "summarize": "summarise", "customize": "customise", "utilize": "utilise",
    "recognize": "recognise", "generalize": "generalise", "specialize": "specialise",
    "modeling": "modelling", "modeled": "modelled",
    "center": "centre", "centered": "centred",
    "catalog": "catalogue", "favorite": "favourite", "neighbor": "neighbour",
    "license": "licence", "gray": "grey", "judgment": "judgement", "practicing": "practising",
}

CTA_HINTS = (
    "let me know", "feel free", "drop me", "get in touch", "reach out", "connect with me",
    "leave a comment", "comment below", "in the comments", "share", "follow", "try it",
    "give it a go", "get your hands dirty", "why wait", "start today", "tell me",
    "what do you think", "would love to hear", "i'd love", "i would love",
)
CLICHE_OPENERS = ("in this article", "in this post", "in this tutorial", "we will learn")
OUTPUT_HINTS = ("output", "returns", "prints", "you'll see", "you will see", "result", "gives you")


@dataclass
class Issue:
    severity: str  # error | warn
    rule: str
    line: int
    message: str


def _strip_code(md: str) -> str:
    """Blank out fenced code (keeping line numbers), inline code and URLs."""
    out, in_fence = [], False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            out.append("")
        else:
            out.append("" if in_fence else line)
    text = "\n".join(out)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"\]\([^)]*\)", "]", text)
    return re.sub(r"https?://\S+", " ", text)


def word_count(md: str) -> int:
    return len(re.findall(r"[A-Za-z0-9'’-]+", _strip_code(md)))


def lint(md: str, *, final: bool = False) -> list[Issue]:
    issues: list[Issue] = []
    lines = md.splitlines()
    prose = _strip_code(md)
    prose_lines = prose.splitlines()

    # Structure
    h1 = [i for i, ln in enumerate(prose_lines, 1) if re.match(r"# \S", ln)]
    if len(h1) != 1:
        issues.append(Issue("error", "title", h1[1] if len(h1) > 1 else 1,
                            f"Expected exactly one H1 title, found {len(h1)}."))
    h2 = [ln for ln in prose_lines if ln.startswith("## ")]
    if len(h2) < 4:
        issues.append(Issue("warn", "structure", 1,
                            f"Only {len(h2)} H2 sections; aim for 4-6 punchy headings."))
    if md.lstrip().startswith("---"):
        issues.append(Issue("error", "format", 1, "No YAML front matter: Medium will paste it."))

    # Length
    words = word_count(md)
    if words < MIN_WORDS or words > MAX_WORDS:
        sev = "error" if (words < MIN_WORDS * 0.8 or words > MAX_WORDS * 1.2) else "warn"
        issues.append(Issue(sev, "length", 1,
                            f"{words} words; target is {MIN_WORDS}-{MAX_WORDS}."))

    # British spelling
    for n, line in enumerate(prose_lines, 1):
        for m in re.finditer(r"[A-Za-z]+", line):
            word = m.group(0).lower()
            if word in US_TO_UK:
                issues.append(Issue("warn", "spelling", n,
                                    f"'{m.group(0)}' -> British '{US_TO_UK[word]}'."))

    # Opening
    first_prose = next((ln for ln in prose_lines if ln.strip() and not ln.startswith("#")), "")
    if first_prose.lower().lstrip("*_ ").startswith(CLICHE_OPENERS):
        issues.append(Issue("warn", "hook",
                            lines.index(first_prose) + 1 if first_prose in lines else 1,
                            "Opens with 'In this article...'. Start with the problem instead."))

    # Em-dash overuse
    dashes = prose.count("—")
    if dashes > 8:
        issues.append(Issue("warn", "punctuation", 1,
                            f"{dashes} em-dashes; the style guide says use periods instead."))

    # Sentence length
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", re.sub(r"^#+ .*$", "", prose, flags=re.M))
                 if s.strip()]
    if sentences:
        avg = sum(len(s.split()) for s in sentences) / len(sentences)
        if avg > 22:
            issues.append(Issue("warn", "readability", 1,
                                f"Average sentence is {avg:.0f} words; keep them short."))

    # Code blocks: explain before, show output after
    fences = [i for i, ln in enumerate(lines, 1) if ln.strip().startswith("```")]
    blocks = list(zip(fences[::2], fences[1::2], strict=False))
    for start, end in blocks:
        lang = lines[start - 1].strip().strip("`").lower()
        if not lang:
            issues.append(Issue("warn", "code", start, "Code block has no language tag."))
        if lang in ("python", "sql", "py", "pyspark"):
            before = next((ln for ln in reversed(lines[: start - 1]) if ln.strip()), "")
            if before.startswith("#") or before.strip().startswith("```"):
                issues.append(Issue("warn", "code", start,
                                    "Code appears without a plain-English intro before it."))
            after = []
            for ln in lines[end:]:
                if ln.startswith("#"):
                    break
                after.append(ln)
                if len(after) > 12:
                    break
            tail = "\n".join(after).lower()
            if "```" not in tail and not any(h in tail for h in OUTPUT_HINTS):
                issues.append(Issue("warn", "code", end,
                                    "No output or result shown after this code block."))

    # Sources and ending
    if len(re.findall(r"\]\(https?://", md)) < 2:
        issues.append(Issue("warn", "sources", 1,
                            "Fewer than 2 inline links; cite official docs or announcements."))
    tail_words = " ".join(md.split()[-150:]).lower()
    if "?" not in tail_words and not any(h in tail_words for h in CTA_HINTS):
        issues.append(Issue("warn", "cta", len(lines),
                            "No call to action or invitation to engage at the end."))

    # Placeholders
    for n, line in enumerate(lines, 1):
        if re.search(r"TODO|TBD|XXX|\[citation needed\]|lorem ipsum|<!--\s*(todo|maxime)",
                     line, re.I):
            issues.append(Issue("error" if final else "warn", "placeholder", n,
                                "Unresolved placeholder: " + line.strip()[:70]))

    return sorted(issues, key=lambda i: (i.severity != "error", i.line))


def lint_file(path: Path, *, final: bool = False) -> list[Issue]:
    return lint(path.read_text(encoding="utf-8"), final=final)
