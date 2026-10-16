# Stop Reminding Claude Code to Check Its Work: Use a Hook Instead

You know the routine. You ask Claude Code to tweak a data file, it makes the change, and you add: "and please run the checks." Next session you forget to say it. Claude forgets too. And a duplicate order ID slips quietly into your pipeline.

Telling an assistant to be careful is the same as sticking a poster on the wall that says "check for smoke". A smoke detector works differently. It reacts every single time, without anyone remembering anything. In Claude Code, that smoke detector is called a **hook**.

Whether you are a seasoned data engineer or just starting out, this is a habit worth building early.

## Why a hook beats a reminder

So why not just ask nicely? Because an instruction in a chat or in your `CLAUDE.md` is a request. Claude will usually follow it, but "usually" is not good enough when bad rows land in a warehouse.

A hook is different. According to the [Claude Code hooks guide](https://code.claude.com/docs/en/hooks-guide.md), hooks are shell commands that run automatically at set points in Claude's workflow, for example every time it edits a file. No memory required, from you or from Claude.

For data work this is a great fit. You can validate a file, run a quick test or lint a query the moment it changes, and the result goes straight back to Claude so it can fix its own mistake.

## The scenario: a messy orders file

Let's use a small, realistic example. We have `data/orders.csv` with customer orders, and three rules we never want broken: no duplicate `order_id`, no missing `amount`, and no negative `amount`.

Here is the file Claude just edited. It contains all three problems on purpose:

```csv
order_id,customer,country,amount
1001,Amara Okafor,NG,42.50
1002,Lars Nielsen,DK,19.99
1002,Lars Nielsen,DK,19.99
1003,Chloé Martin,FR,-5.00
1004,Sofia Rossi,IT,
```

Row `1002` appears twice, `1003` has a negative amount, and `1004` has no amount at all. Easy to spot in five rows. Much harder in five million.

## Step 1: write the check

A hook is just a script that receives a small JSON message on standard input. For file edits, that message includes the path of the file that changed under `tool_input.file_path`. The script below reads it, ignores every file except `orders.csv`, and collects any problems it finds.

```python
#!/usr/bin/env python3
"""PostToolUse hook: validate data/orders.csv after Claude edits it."""
import csv
import json
import sys
from pathlib import Path

payload = json.load(sys.stdin)
path = Path(payload["tool_input"]["file_path"])
if path.name != "orders.csv":
    sys.exit(0)  # not our file, stay silent

problems, seen = [], set()
with path.open(newline="", encoding="utf-8") as f:
    for line_no, row in enumerate(csv.DictReader(f), start=2):
        if row["order_id"] in seen:
            problems.append(f"line {line_no}: duplicate order_id {row['order_id']}")
        seen.add(row["order_id"])
        if not row["amount"]:
            problems.append(f"line {line_no}: missing amount for order {row['order_id']}")
        elif float(row["amount"]) < 0:
            problems.append(f"line {line_no}: negative amount {row['amount']}")

if problems:
    print("orders.csv failed validation:\n" + "\n".join(problems), file=sys.stderr)
    sys.exit(2)  # PostToolUse can't undo the edit, but Claude sees stderr
```

Save it as `.claude/hooks/check_orders.py`. When the file is clean, the script prints nothing at all and exits quietly. The last two lines are the important ones, and we will come back to them.

## Step 2: tell Claude Code when to run it

Now we connect the script to an event. Add this to `.claude/settings.json` in your project:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/check_orders.py\""
          }
        ]
      }
    ]
  }
}
```

`PostToolUse` means "after a tool call succeeds". The `Edit|Write` matcher limits it to tools that change files, so your hook does not wake up for every command Claude runs. `$CLAUDE_PROJECT_DIR` points to the project root where the session started, so the path keeps working even if Claude moves into a subfolder. Type `/hooks` in Claude Code afterwards to confirm that it shows up.

## Step 3: watch it catch the mistakes

Here is what the script prints when it receives the edit message for our messy file. I ran this locally to get the real output:

```text
orders.csv failed validation:
line 4: duplicate order_id 1002
line 5: negative amount -5.00
line 6: missing amount for order 1004
```

The exit code was 2. Claude Code shows that message to Claude, which now knows exactly which lines to fix, and it does so without you typing a word. When Claude removes the duplicate and the broken rows, the script stays silent and exits with 0. Silence means all clear.

## Make it narrower, then smarter

Our hook works. But can we make it a little more polite? Running Python on every file edit is a bit wasteful. The hooks reference describes an optional `if` field that uses the same pattern syntax as permission rules, such as `Edit(*.ts)`, so the command only runs when the tool call matches. For our case, that means adding `"if": "Edit(*.csv)"` next to `"type": "command"`. The file-name check inside the script then becomes a safety net rather than the only gatekeeper.

Once the check works, you can also make it friendlier. Instead of failing, a hook can exit with 0 and print a small JSON message. This one nudges Claude to run a row count after a successful edit:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "orders.csv changed. Run a row count and compare it with yesterday's load before moving on."
  }
}
```

Claude Code wraps that string in a system reminder and slips it into the conversation. It does not show up as a chat message for you, but Claude reads it on its next step. That is how you turn a hook from a strict gatekeeper into a helpful colleague, and the same trick works for reminders such as "remember to run `dbt test` on the models you touched".

## Where hooks go quiet: exit codes

Why might a hook look like it does nothing? Usually the answer is an exit code. The [hooks reference](https://code.claude.com/docs/en/hooks.md) has three details that are easy to miss.

First, **exit code 1 does not mean "failure" to Claude Code**. It is treated as a non-blocking error, which you see as a notice but which does not enforce anything. If a hook is meant to enforce a rule, use exit code 2.

Second, **a hook that exits 0 stays invisible to Claude**. For most events, including `PostToolUse`, its stdout goes to the debug log, and Claude never sees its stderr. So `print("looks fine")` will not tell Claude anything. If you want to pass information along on success, return JSON with an `additionalContext` field, which Claude Code inserts into the conversation as a system reminder.

Third, **a `PostToolUse` hook cannot block the edit**, because the tool has already run. Exit code 2 here means "show this to Claude", not "undo it". If you want to stop a change before it happens, you need a `PreToolUse` hook instead.

<!-- maxime: Add 2-3 sentences about a real time a data check was skipped or a bad file slipped through in your own work, and how long it took to notice. -->

## Your first hook this week

Think of the check you most often remind Claude about. A row count, a schema comparison, a SQL linter, `dbt test` on the model you just touched. Write it as a small script, wire it to `PostToolUse` with a narrow matcher, and test it once with a deliberately broken file, exactly like we did above.

Remember the smoke detector? You do not have to remember to be careful anymore. You just have to install the detector once. Start with the smallest check you can think of, and let me know in the comments which one you picked. I would love to hear what you automate first! 🙌
