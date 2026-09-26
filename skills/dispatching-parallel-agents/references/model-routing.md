# Role-to-model routing

Read this reference before dispatch. This is policy interpreted by the agent, not a native Codex configuration file or executable resolver. The workflow in `../SKILL.md` uses stable roles; maintain concrete model IDs and effort preferences here. Current user instructions override these defaults, subject to runtime capabilities and higher-priority instructions.

## Approved mapping

This mapping implements the user's Luna-first, architect-on-demand workflow and latest executor/reviewer override using models exposed by the collaboration runtime on 2026-09-26. Validate it afresh in each task; the date is evidence of a checked snapshot, not a promise of future availability.

| Role | Preferred model | Effort policy | Approved alternative model |
| --- | --- | --- | --- |
| `coordinator` | `gpt-6-luna` | First supported: `ultra`, then `xhigh` | None |
| `explorer` | `gpt-6-luna` | First supported: `ultra`, then `xhigh` | None |
| `executor` | `gpt-6-astra` | `low` | None |
| `reviewer` | `gpt-6-astra` | `low`; use an agent independent of the implementation author | None |
| `architect` | `gpt-6-astra` | `medium` initially | None |

The user selected `gpt-6-astra` with `low` effort for both executor and reviewer. These roles remain distinct from the architect, even though they share its model family. Routine executor/reviewer requests do not consume the architect-escalation budget; record their actual model usage separately from role-based escalation counts. Review still requires an agent independent of the implementation author. Concrete model names are bindings, not the definitions of the roles.

The user's latest Luna preference is `ultra` when supported, otherwise `xhigh`, for both coordinator and explorer. In the checked snapshot, `gpt-6-luna` supports `xhigh` and `max`, but not `ultra`, so that snapshot resolves to `xhigh`. Live support takes precedence over this dated observation. Do not select `max` just because it is available. If neither preferred effort is supported, report the unsupported binding rather than silently lowering the preference.

For architect work, raise effort to `high` only when `medium` has not resolved the decision. Higher levels require an explicit escalation choice and runtime support; they remain subject to the task's architect-request budget. A higher effort is not a reason to restart the request counter.

## Resolve against the live tool

1. Read the schema and model/effort metadata of the actual subagent spawn tool. A website catalog, API model list, cache, or separate task-creation tool does not establish availability for this tool. Do not spawn a probe solely to discover availability.
2. Resolve each needed role against this mapping or a user's explicit task override. Check the exact model ID, supported effort, tool fields, concurrency capacity, and any applicable project constraints. Do not pass role names as model IDs or invent tool arguments.
3. Select the first supported approved effort in that role's ordered preference. For a fixed effort, require that exact value. Use supported explicit spawn fields or a verified runtime configuration that establishes the effective model and effort. If neither can establish the approved binding, mark the choice unverified, report the limitation, and do not dispatch that dependent agent. Do not assert support from memory or rely on unverified inheritance.
4. Announce the resolved role/model/effort mapping once before dispatch, including any approved fallback and its reason. Reuse this resolution within the task unless availability or the user's choice changes.
5. If a required model is unavailable, use only an explicitly approved alternative. This initial mapping has none. Report the affected role and ask for a replacement only when needed to continue that dependent work; advance unrelated work whose bindings and permissions remain valid. A model retirement must not silently convert routine work into architect work.
6. A new version number, familiar family name, or higher price does not prove equivalent capability. After a user approves a replacement, apply it to the authorized task; update this reference only when persistent configuration changes are also authorized, and validate representative tasks. The generic workflow should not require rewriting.

Treat `429`, transient transport errors, and capacity failures separately from an unsupported model/effort. Use bounded retries consistent with the runtime and workflow; preserve the request budget and evidence. Never open repeated agents or switch to a more expensive model just to evade a rate limit.

## Main model and inheritance

A skill cannot switch the model of the running main task. For the intended cost profile, select the coordinator model and resolved effort in the app before starting the task. Do not edit app configuration merely because this skill is loaded.

Compare the actual main model and effort with the resolved coordinator binding when those facts are exposed. Disclose a mismatch once, or state that a model/effort value cannot be verified if it is not exposed; let the existing main carry the necessary coordination for this task. Its routine turns are not architect escalations, but their model usage still counts in metrics. Do not claim Luna is main, or spawn a Luna coordinator while the expensive main duplicates all of its reasoning. Route disjoint work through verified bindings and explain that the desired main-model cost profile is not established for this task when the main binding differs or cannot be verified. This exception for an already-running main does not permit spawning an unverified subagent.

Where runtime configuration supports agent-specific or default model/effort settings, those settings can supply bindings, but inspect the resolved behavior before relying on them. Omitted spawn fields may inherit the parent's model or effort; inheritance is not automatically a low-cost fallback. This reference neither creates custom agents nor changes runtime configuration.

## Maintenance and evidence

Keep one maintained mapping in the project skill, and synchronize the reference with the installed skill. `AGENTS.md` and the repository README should refer to roles and this mapping rather than duplicate model IDs. Explicit project/task pins still apply; report conflicts instead of overriding them silently.

After a mapping change, exercise at least: simple read-only work, clear implementation, an architectural decision, an unavailable model, unsupported effort, a transient failure, and a main-model mismatch. Verify routes and reporting before using usage targets as acceptance evidence. Compare real usage and quality over the rollout window described in `SKILL.md`; never infer savings from model names alone.
