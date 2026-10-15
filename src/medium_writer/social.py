"""Checks for short-form social posts derived from an article (LinkedIn)."""

import re
from dataclasses import dataclass

LINKEDIN_MAX = 3000
LINKEDIN_HOOK = 210  # characters visible before "see more"


@dataclass
class SocialIssue:
    severity: str
    message: str


def check_linkedin(text: str) -> list[SocialIssue]:
    issues: list[SocialIssue] = []
    text = text.strip()
    if len(text) > LINKEDIN_MAX:
        issues.append(SocialIssue("error", f"{len(text)} characters; LinkedIn allows {LINKEDIN_MAX}."))
    first = text.splitlines()[0] if text else ""
    if len(first) > LINKEDIN_HOOK:
        issues.append(SocialIssue("warn", f"Hook line is {len(first)} chars; only ~{LINKEDIN_HOOK} show before 'see more'."))
    tags = re.findall(r"(?<!\w)#\w+", text)
    if len(tags) > 5:
        issues.append(SocialIssue("warn", f"{len(tags)} hashtags; use at most 3-5."))
    if re.search(r"https?://", first):
        issues.append(SocialIssue("warn", "Link in the hook line; put it later or in the first comment."))
    if "?" not in text[-300:]:
        issues.append(SocialIssue("warn", "No closing question to invite comments."))
    if re.search(r"\b(analyze|color|behavior|organize|optimize)\b", text, re.I):
        issues.append(SocialIssue("warn", "American spelling found; use British spelling."))
    return issues
