#!/usr/bin/env python3
"""Post a Claude code review comment on a GitHub PR using the Anthropic API."""
import anthropic
import os
import subprocess
import sys

diff = open("/tmp/pr.diff").read()
if len(diff) > 30000:
    diff = diff[:30000] + "\n\n... (diff truncated at 30k chars)"

if not diff.strip():
    print("Empty diff, skipping review")
    sys.exit(0)

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
msg = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": f"""Review this PR diff for the Bitcoin Counters webapp (metaver5o/counters-proto).

Focus ONLY on high-confidence issues:
1. Correctness bugs — Bitcoin tx logic, Counterparty asset rules, wallet signing
2. Security — XSS, API key in JS bundle, unsafe iframe sandbox attributes
3. Svelte 5 rune misuse — $effect writing state, $derived with side effects
4. API contract — field names against /counters /counter/:id /status
5. Simplification — unnecessary abstractions, dead code

Skip style nits. If the diff looks clean, say so in one sentence.
Format: markdown bullet list. Keep it under 300 words.

```diff
{diff}
```"""
    }]
)

review = msg.content[0].text
body = f"## 🤖 Claude Code Review\n\n{review}\n\n---\n*Powered by claude-sonnet-4-6 via Anthropic API*"

pr = os.environ["PR_NUMBER"]
repo = os.environ["REPO"]
result = subprocess.run(
    ["gh", "pr", "comment", pr, "--repo", repo, "--body", body],
    capture_output=True, text=True
)
if result.returncode != 0:
    print(f"Failed to post comment: {result.stderr}", file=sys.stderr)
    sys.exit(1)
print("Review posted successfully")
