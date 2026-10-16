# Research brief: Claude Code hooks for data engineers: run your tests automatically

Status: dry run, drafted. Target 1000–1800 words.

## 1. Angle
Stop re-telling Claude Code to check its work: a ~20-line PostToolUse hook validates your data files after every edit and feeds failures straight back to Claude.

## 2. Reader's starting point
Knows Python/SQL and has tried Claude Code. Confused by: why a hook "did nothing", what exit codes mean, difference between hooks and CLAUDE.md instructions.

## 3. Primary sources
| # | Source | Type | Retrieved | Archived |
|---|---|---|---|---|
| 1 | https://code.claude.com/docs/en/hooks-guide.md | official docs | 2026-10-16 | sources/01 |
| 2 | https://code.claude.com/docs/en/hooks.md | official reference | 2026-10-16 | sources/03 |
| 3 | https://code.claude.com/docs/en/skills.md | official docs | 2026-10-16 | sources/02 (truncated) |

## 4. Claims ledger
| Claim | Src | Verified |
|---|---|---|
| Hooks are shell commands that run automatically at lifecycle points | 1 | yes |
| PostToolUse fires after a tool call succeeds | 2 (event table) | yes |
| `matcher: "Edit\|Write"` limits it to file-editing tools; hook gets JSON on stdin with `tool_input.file_path` | 1 (Prettier example) | yes |
| Exit 0: stdout goes to debug log, not shown to Claude (except UserPromptSubmit, UserPromptExpansion, SessionStart, PostModelSwitch) | 2 | yes |
| Exit 0: Claude never sees stderr | 2 | yes |
| Exit 2 on PostToolUse: "Shows stderr to Claude; the tool already ran" (cannot block) | 2 (exit-code table) | yes |
| Any other non-zero exit (e.g. 1) is a non-blocking error; to enforce policy use exit 2 | 2 | yes |
| `hookSpecificOutput.additionalContext` is inserted as a system reminder | 2 | yes |
| `$CLAUDE_PROJECT_DIR` available in hook commands; `/hooks` shows configured hooks | 1, 2 | yes |
| `if` field filters by permission-rule syntax e.g. `Edit(*.ts)` | 2 | yes |
| Demo output (duplicate / negative / missing amount) | n/a | ran locally, real output |

## 5. Analogy
A hook is a smoke detector, CLAUDE.md is a poster saying "please be careful": one reacts every time, the other relies on remembering.

## 8. Personal angle (needs Maxime)
- Which data checks did he repeatedly have to remind Claude about?
- A time an unvalidated CSV/SQL change slipped through?
