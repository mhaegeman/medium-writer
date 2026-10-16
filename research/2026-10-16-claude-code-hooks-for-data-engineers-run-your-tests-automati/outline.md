# Outline (dry run: normally this stops for approval)

Titles: (1) "Stop Reminding Claude Code to Check Its Work: Use a Hook Instead" (2) "A 20-Line Hook That Makes Claude Code Validate Your Data" (3) "Claude Code Hooks for Data Engineers"
Hook: you keep typing "and run the checks please"; Claude forgets. Analogy: smoke detector vs poster.
H2s: The "please remember" problem · What a hook actually is · Build it: validate orders.csv after every edit · Wire it up in settings.json · See it catch real mistakes · What I got wrong (exit codes) · Your first hook this week
Code: orders.csv; check_orders.py; settings.json; run output (real).
Mistake section: exit 1 vs 2, stdout invisible; personal story = placeholder.
Close: callback to smoke detector; try one hook on your most-forgotten check; invite comments.
