# Codex Skills

Personal skills for Codex.

## Available skills

- [dispatching-parallel-agents](skills/dispatching-parallel-agents/SKILL.md): Review tasks, tickets, and Flows for independent work, then coordinate agents with explicit dependencies and file ownership. Includes a local policy using GPT-6 Astra for coordination/review and GPT-5.6 Luna (`max`) for implementation and scoped tests.

## Install

Copy the desired skill directory into your Codex skills directory (by default, `~/.codex/skills/`). From this repository on Windows PowerShell:

```powershell
$skillsDirectory = Join-Path $env:USERPROFILE '.codex/skills'
New-Item -ItemType Directory -Path $skillsDirectory -Force | Out-Null
Copy-Item -LiteralPath './skills/dispatching-parallel-agents' -Destination $skillsDirectory -Recurse -Force
```

If you use a custom `CODEX_HOME`, use its `skills` directory instead. Back up any local customization before replacing an existing skill.

## Origin

`dispatching-parallel-agents` identifies itself as a local customization of `obra/superpowers`. Its upstream attribution and local coordination policy are preserved in `SKILL.md`.
