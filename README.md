# Codex Skills

Personal skills for Codex.

## Available skills

- [design-taste-frontend](skills/design-taste-frontend/SKILL.md): Anti-slop frontend direction for landing pages, portfolios, and redesigns.
- [dispatching-parallel-agents](skills/dispatching-parallel-agents/SKILL.md): Review tasks, tickets, and Flows for independent work, then coordinate agents with explicit dependencies and file ownership. The local policy assigns Astra read-only research, analysis, planning, coordination, review, and final evidence assessment; Luna (`max`) performs all execution, including implementation, integration fixes, authorized documentation/ticket records, and tests.

  The role sequence is Astra research/analysis/planning/dispatch → Luna implementation/integration → Astra read-only review → Luna fixes and documentation → Luna final tests → Astra final review and evidence summary. Luna may run useful scoped tests early, but final evidence follows final code/docs edits; record-only changes need applicable documentation checks, while behavior changes require affected runtime tests again. If final changes affect reviewed content, repeat the review and affected tests. Luna records Astra's actual verdict and blockers faithfully; it never self-approves. The skill cannot change the running main model, and a missing required model is reported rather than silently substituted.
- [find-skills](skills/find-skills/SKILL.md): Discover and install skills from the agent skills ecosystem.
- [gpt-taste](skills/gpt-taste/SKILL.md): High-end UX/UI and GSAP motion engineering guidance.
- [huashu-design](skills/huashu-design/SKILL.md): HTML-based high-fidelity prototypes, slides, animations, visualizations, and design reviews.
- [minimalist-ui](skills/minimalist-ui/SKILL.md): Clean editorial-style interface direction with warm monochrome palettes and flat bento grids.
- [redesign-existing-projects](skills/redesign-existing-projects/SKILL.md): Audit and upgrade existing websites and apps without breaking functionality.
- [skill-ticket-manage](skills/skill-ticket-manage/SKILL.md): Spec-first ticket, Flow, review, audit, and closeout workflows.

## Install

Copy the desired skill directory into your Codex skills directory (by default, `~/.codex/skills/`). From this repository on Windows PowerShell:

```powershell
$skillsDirectory = Join-Path $env:USERPROFILE '.codex/skills'
New-Item -ItemType Directory -Path $skillsDirectory -Force | Out-Null
Copy-Item -Path './skills/*' -Destination $skillsDirectory -Recurse -Force
```

If you use a custom `CODEX_HOME`, use its `skills` directory instead. Back up any local customization before replacing an existing skill.

## Origin

`dispatching-parallel-agents` identifies itself as a local customization of `obra/superpowers`. Its upstream attribution and local coordination policy are preserved in `SKILL.md`.
