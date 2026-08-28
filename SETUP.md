# Claude Skills — Setup Guide

Skills live at `~/.claude/skills/`. This directory is a git repo synced to GitHub.
A `SessionStart` hook pulls the latest on every Claude Code session automatically.

## First Machine (initialise the repo)

```powershell
cd "$env:USERPROFILE\.claude\skills"
git init
git remote add origin https://github.com/<your-username>/claude-skills.git
git add .
git commit -m "initial skills"
git push -u origin main
```

## Every Subsequent Machine (clone)

```powershell
git clone https://github.com/<your-username>/claude-skills "$env:USERPROFILE\.claude\skills"
```

## SessionStart Hook

Add this block to `~/.claude/settings.json` (merge into existing JSON, do not replace the file):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd \"$env:USERPROFILE\\.claude\\skills\" && git pull --ff-only --quiet 2>$null"
          }
        ]
      }
    ]
  }
}
```

`--ff-only` means if you have local uncommitted edits, the pull is skipped (your edits are never overwritten).

## Day-to-Day Workflow

| Action | Command |
|---|---|
| After editing a skill | `git add . && git commit -m "..." && git push` |
| New machine setup | `git clone ...` (once only) |
| Check sync status | `git status` inside `~/.claude/skills/` |
