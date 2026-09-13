---
name: commit-message
description: Use when asked to write, generate, draft, or shorten a git commit message
allowed-tools:
  - Bash(git status *)
  - Bash(git diff *)
---

# Commit Message

## Overview

Gives the user a ready-to-run `git commit` command in their own voice. The user stages and commits; this skill only reads.

## Steps

1. With the Bash tool, run in parallel: `git status --short --branch` and `git diff --cached --stat`
2. Pick what to describe:
   - Anything staged: the staged changes (`git diff --cached`)
   - Nothing staged: all changes (`git diff HEAD`), plus untracked `??` files, read directly
   - No changes at all: reply `No changes to commit.` and stop
3. For a large diff, run the matching `--stat` first and read only the files that carry the change. Skip lockfiles and generated files.
4. Write the message, then the reply.

## The message

- **Summary:** opens with an -ing verb (Adding, Fixing, Updating, Removing, Moving) and joins separate changes with a plus sign, as in `Adding task timeout fix + workflow rename`. 72 characters max.
- **Body:** only when the summary can't cover the change in 72 characters. One line, comma-separated, same voice, 160 characters max.
- **Characters:** plain words and punctuation. Rephrase anything that would need `"`, `$`, a backtick, `\` or `!`, so the command runs unchanged in PowerShell and bash.

## The reply

Exactly these parts, in order:

1. Nothing staged: the line `Nothing is staged. To stage everything:` then a `bash` block containing `git add -A`
2. Something staged while other changes or new files are not: the line `Only staged changes are included.`
3. A `bash` block with the command, one `-m` for the summary and a second `-m` for the body:

```bash
git commit -m "Fixing event-loop stall on segment rotation + concurrency races" -m "Flushing PCM off-thread, locking Whisper and playback, unique clip names, Dockerfile env name fix. Adding config.py, pinned deps, tests."
```

Asked for shorter: drop the body. With no body, tighten the summary.

New files get read, not staged. The user runs `git add` and `git commit`.
