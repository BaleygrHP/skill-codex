#!/usr/bin/env python3
"""Portable spec-first ticket workflow CLI. Uses only the standard library."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path


DEFAULT_CONFIG = {
    "issue_dir": "Issue",
    "prefix": "TD",
    "digits": 6,
    "required_files": [
        "README.md",
        "spec.md",
        "discuss.md",
        "diff-note.md",
        "review.md",
        "outscope.md",
    ],
    "statuses": ["OPEN", "SPEC-READY", "IN-PROGRESS", "IN-REVIEW", "DONE"],
    "flow_dir": "FLOW",
    "flow_prefix": "FL",
    "flow_digits": 6,
    "flow_statuses": ["DRAFT", "PLANNED", "ACTIVE", "VALIDATING", "DONE", "BLOCKED", "CANCELLED"],
}

REVIEW_SCOPE_FILE = "reviewed-files.json"
NORMALIZED_REVIEW_METADATA = (
    "Unlocks",
    "Review status",
    "Reviewed change fingerprint",
    "Status",
    "Done",
    "Completed at",
)
TICKET_METADATA_MARKERS = {
    "Unlocks": "<generated>",
    "Review status": "<generated>",
    "Reviewed change fingerprint": "<excluded>",
    "Status": "<status>",
    "Done": "<done>",
    "Completed at": "<completed>",
}


def project_path(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"project directory does not exist: {path}")
    return path


def load_config(project: Path) -> dict:
    path = project / ".ticket-workflow.json"
    if not path.exists():
        return dict(DEFAULT_CONFIG)
    data = json.loads(path.read_text(encoding="utf-8"))
    config = dict(DEFAULT_CONFIG)
    config.update(data)
    return config


def ticket_pattern(config: dict) -> re.Pattern[str]:
    return re.compile(
        rf"^{re.escape(config['prefix'])}(?P<number>\d{{{int(config['digits'])}}})$"
    )


def issue_path(project: Path, config: dict) -> Path:
    return project / str(config["issue_dir"])


def flow_path(project: Path, config: dict) -> Path:
    return project / str(config.get("flow_dir", "FLOW"))


def id_pattern(prefix: str, digits: int) -> re.Pattern[str]:
    return re.compile(rf"^{re.escape(prefix)}(?P<number>\d{{{int(digits)}}})$")


def ticket_dirs(project: Path, config: dict) -> list[Path]:
    root = issue_path(project, config)
    pattern = ticket_pattern(config)
    if not root.is_dir():
        return []
    return sorted(
        (entry for entry in root.iterdir() if entry.is_dir() and pattern.fullmatch(entry.name)),
        key=lambda item: item.name,
    )


def flow_pattern(config: dict) -> re.Pattern[str]:
    return id_pattern(str(config.get("flow_prefix", "FL")), int(config.get("flow_digits", 6)))


def flow_dirs(project: Path, config: dict) -> list[Path]:
    root = flow_path(project, config)
    pattern = flow_pattern(config)
    if not root.is_dir():
        return []
    return sorted(
        (entry for entry in root.iterdir() if entry.is_dir() and pattern.fullmatch(entry.name)),
        key=lambda item: item.name,
    )


def next_ticket_id(project: Path, config: dict) -> str:
    pattern = ticket_pattern(config)
    numbers = [
        int(pattern.fullmatch(path.name).group("number"))
        for path in ticket_dirs(project, config)
    ]
    number = max(numbers, default=0) + 1
    return f"{config['prefix']}{number:0{int(config['digits'])}d}"


def next_flow_id(project: Path, config: dict) -> str:
    pattern = flow_pattern(config)
    numbers = [
        int(pattern.fullmatch(path.name).group("number"))
        for path in flow_dirs(project, config)
    ]
    number = max(numbers, default=0) + 1
    return f"{config.get('flow_prefix', 'FL')}{number:0{int(config.get('flow_digits', 6))}d}"


def replace_tokens(text: str, ticket_id: str, title: str, opened: str) -> str:
    return (
        text.replace("TDxxxxxx", ticket_id)
        .replace("FLxxxxxx", ticket_id)
        .replace("<short title>", title)
        .replace("YYYY-MM-DD", opened)
    )


def replace_flow_tokens(text: str, flow_id: str, title: str, created: str) -> str:
    return (
        text.replace("FLxxxxxx", flow_id)
        .replace("<flow title>", title)
        .replace("YYYY-MM-DD", created)
    )


def update_next_marker(project: Path, config: dict) -> None:
    index = issue_path(project, config) / "README.md"
    if not index.exists():
        return
    text = index.read_text(encoding="utf-8")
    replacement = (
        "<!-- NEXT_TICKET -->\n"
        f"**Next ticket:** `{next_ticket_id(project, config)}`\n"
        "<!-- /NEXT_TICKET -->"
    )
    updated, count = re.subn(
        r"<!-- NEXT_TICKET -->.*?<!-- /NEXT_TICKET -->",
        replacement,
        text,
        flags=re.DOTALL,
    )
    if count:
        index.write_text(updated, encoding="utf-8", newline="\n")


def command_init(args: argparse.Namespace) -> int:
    project = args.project
    starter = Path(__file__).resolve().parent.parent / "assets" / "project-starter"
    sources = [source for source in starter.rglob("*") if source.is_file()]
    conflicts = [
        source.relative_to(starter)
        for source in sources
        if (project / source.relative_to(starter)).exists()
    ]
    if conflicts and not args.merge:
        print("Refusing initialization; existing targets:", file=sys.stderr)
        for path in conflicts:
            print(f"  {path}", file=sys.stderr)
        print("Use --merge to copy only missing files without overwriting.", file=sys.stderr)
        return 2
    copied = 0
    for source in sources:
        relative = source.relative_to(starter)
        target = project / relative
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1
    print(f"Initialized {copied} files in {project}")
    return 0


def command_new(args: argparse.Namespace) -> int:
    project = args.project
    config = load_config(project)
    template = issue_path(project, config) / "_TEMPLATE"
    if not template.is_dir():
        print(f"Missing template directory: {template}", file=sys.stderr)
        return 2
    ticket_id = next_ticket_id(project, config)
    target = issue_path(project, config) / ticket_id
    target.mkdir(parents=False, exist_ok=False)
    opened = args.opened or date.today().isoformat()
    for source in template.iterdir():
        if not source.is_file():
            continue
        text = source.read_text(encoding="utf-8")
        (target / source.name).write_text(
            replace_tokens(text, ticket_id, args.title, opened),
            encoding="utf-8",
            newline="\n",
        )
    update_next_marker(project, config)
    print(target)
    return 0


def parse_status(readme: Path) -> str | None:
    if not readme.exists():
        return None
    match = re.search(
        r"^\*\*Status:\*\*\s*([A-Z][A-Z-]*)\s*$",
        readme.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    return match.group(1) if match else None


def parse_markdown_metadata(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    metadata: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\*\*([^:*]+):\*\*\s*(.*)$", line)
        if match:
            key = match.group(1).strip().lower().replace(" ", "_").replace("-", "_")
            metadata[key] = match.group(2).strip()
    return metadata


def write_metadata_field(path: Path, label: str, value: str) -> bool:
    text = path.read_text(encoding="utf-8")
    pattern = rf"^(\*\*{re.escape(label)}:\*\*)[ \t]*.*$"
    replacement = rf"\1 {value}"
    updated, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if count == 0:
        lines = text.splitlines()
        insert_at = 1
        while insert_at < len(lines) and lines[insert_at].startswith("**"):
            insert_at += 1
        lines.insert(insert_at, f"**{label}:** {value}")
        updated = "\n".join(lines) + "\n"
    if updated != text:
        path.write_text(updated, encoding="utf-8", newline="\n")
        return True
    return False


def csv_values(value: str | None) -> list[str]:
    if not value or value.lower() in {"none", "-", "n/a"}:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def placeholder_found(text: str) -> bool:
    return bool(re.search(r"<[^>\n]+>", text))


def audit_ticket(path: Path, config: dict, *, closeout: bool = False) -> list[str]:
    errors: list[str] = []
    for name in config["required_files"]:
        if not (path / name).is_file():
            errors.append(f"missing {name}")
    readme = path / "README.md"
    status = parse_status(readme)
    if status not in config["statuses"]:
        errors.append(f"invalid or missing status: {status!r}")
    if status != "DONE" and not closeout:
        return errors

    readme_text = readme.read_text(encoding="utf-8")
    if "- [ ]" in readme_text:
        errors.append("DONE ticket has unchecked resolve items")
    if status == "DONE" and re.search(
        r"^\*\*Done:\*\*\s*(—|-|TBD)\s*$", readme_text, re.MULTILINE
    ):
        errors.append("DONE ticket has no completion date")

    spec = path / "spec.md"
    if spec.exists():
        spec_text = spec.read_text(encoding="utf-8")
        if "Acceptance Criteria" not in spec_text:
            errors.append("spec has no Acceptance Criteria section")
        if placeholder_found(spec_text):
            errors.append("spec still contains placeholders")

    diff_note = path / "diff-note.md"
    if diff_note.exists():
        diff_text = diff_note.read_text(encoding="utf-8")
        if "Tests run" not in diff_text or placeholder_found(diff_text):
            errors.append("diff-note has no concrete test evidence or contains placeholders")

    review = path / "review.md"
    if review.exists():
        review_text = review.read_text(encoding="utf-8")
        if not re.search(r"\b(PASS|APPROVED)\b", review_text, re.IGNORECASE):
            errors.append("review has no PASS or APPROVED verdict")
        if re.search(r"\bPENDING\b", review_text, re.IGNORECASE):
            errors.append("review still contains PENDING")
    return errors


def ticket_dir(project: Path, config: dict, ticket_id: str) -> Path:
    return issue_path(project, config) / ticket_id


def flow_dir(project: Path, config: dict, flow_id: str) -> Path:
    return flow_path(project, config) / flow_id


def linked_tickets(project: Path, config: dict, flow_id: str) -> list[Path]:
    linked = []
    for path in ticket_dirs(project, config):
        metadata = parse_markdown_metadata(path / "README.md")
        if metadata.get("flow_id") == flow_id:
            linked.append(path)
    return linked


def ticket_status(path: Path) -> str:
    return parse_status(path / "README.md") or "UNKNOWN"


def ticket_title(path: Path) -> str:
    readme = path / "README.md"
    if not readme.exists():
        return path.name
    first = readme.read_text(encoding="utf-8").splitlines()[0].lstrip("#").strip()
    return first or path.name


def git_output(project: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=project,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return ""
    return result.stdout.replace("\r\n", "\n")


def normalized_file_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    if path.name == "README.md":
        for generated_label in NORMALIZED_REVIEW_METADATA:
            text = re.sub(
                rf"^(\*\*{re.escape(generated_label)}:\*\*)[ \t]*.*$",
                rf"\1 {TICKET_METADATA_MARKERS[generated_label]}",
                text,
                flags=re.MULTILINE,
            )
    if path.name == "review.md":
        text = re.sub(
            r"^(\*\*Change fingerprint:\*\*)[ \t]*.*$",
            r"\1 <excluded>",
            text,
            flags=re.MULTILINE,
        )
    return text


def workflow_exclusions(config: dict) -> list[str]:
    flow_root_name = str(config.get("flow_dir", "FLOW")).replace("\\", "/")
    issue_root_name = str(config.get("issue_dir", "Issue")).replace("\\", "/")
    return [f":(exclude){flow_root_name}/**", f":(exclude){issue_root_name}/**"]


def is_review_generated_artifact(config: dict, ticket: Path, relative: str) -> bool:
    """Return whether a configured generated artifact is outside the digest.

    Projects with cross-repository evidence may regenerate commit-bound JSON
    after a review freeze. The project config owns the small explicit allowlist;
    ordinary ticket evidence remains fingerprinted unless it is named there.
    """

    configured = config.get("review_artifact_exclusions", [])
    if not isinstance(configured, list):
        return False
    for raw in configured:
        pattern = str(raw).replace("\\", "/").strip()
        if pattern.startswith(ticket.name + "/"):
            pattern = pattern[len(ticket.name) + 1 :]
        if pattern and fnmatch.fnmatchcase(relative, pattern):
            return True
    return False


def _safe_review_path(project: Path, value: str) -> str:
    normalized = str(value).replace("\\", "/").strip()
    candidate = Path(normalized)
    if not normalized or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"reviewed path must stay inside the project: {value!r}")
    relative = candidate.as_posix()
    while relative.startswith("./"):
        relative = relative[2:]
    if not relative:
        raise ValueError(f"invalid reviewed path: {value!r}")
    return relative


def _canonical_scope_bytes(path: Path) -> bytes:
    """Hash reviewed text independently of the checkout's EOL policy."""

    content = path.read_bytes()
    if b"\x00" in content:
        return content
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return content
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _scope_entry(project: Path, relative_name: str) -> dict[str, str]:
    path = project / relative_name
    if path.is_symlink():
        raise ValueError(f"reviewed path cannot be a symlink: {relative_name}")
    if path.is_file():
        content = _canonical_scope_bytes(path)
        if path.name == "README.md":
            text = content.decode("utf-8", errors="replace").replace("\r\n", "\n")
            for generated_label in NORMALIZED_REVIEW_METADATA:
                text = re.sub(
                    rf"^(\*\*{re.escape(generated_label)}:\*\*)[ \t]*.*$",
                    r"\1 <generated>",
                    text,
                    flags=re.MULTILINE,
                )
            content = text.encode("utf-8")
        return {
            "path": relative_name,
            "expected": "present",
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    if path.exists():
        raise ValueError(f"reviewed path is not a file: {relative_name}")
    return {"path": relative_name, "expected": "absent", "sha256": ""}


def discovered_review_paths(project: Path, config: dict) -> list[str]:
    exclusions = workflow_exclusions(config)
    raw = git_output(
        project,
        ["diff", "--name-status", "-z", "--find-renames", "HEAD", "--", ".", *exclusions],
    )
    tokens = raw.split("\0")
    paths: set[str] = set()
    index = 0
    while index < len(tokens):
        status = tokens[index]
        index += 1
        if not status:
            continue
        if status.startswith(("R", "C")):
            if index + 1 >= len(tokens):
                raise ValueError("malformed git rename/copy status")
            paths.add(_safe_review_path(project, tokens[index]))
            paths.add(_safe_review_path(project, tokens[index + 1]))
            index += 2
        else:
            if index >= len(tokens):
                raise ValueError("malformed git status")
            paths.add(_safe_review_path(project, tokens[index]))
            index += 1
    untracked = git_output(
        project,
        ["ls-files", "--others", "--exclude-standard", "--", ".", *exclusions],
    )
    paths.update(
        _safe_review_path(project, line)
        for line in untracked.splitlines()
        if line.strip()
    )
    return sorted(paths)


def load_review_scope(ticket: Path) -> dict | None:
    path = ticket / REVIEW_SCOPE_FILE
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or payload.get("ticket_id") != ticket.name:
        raise ValueError(f"invalid {REVIEW_SCOPE_FILE} for {ticket.name}")
    files = payload.get("files")
    if not isinstance(files, list):
        raise ValueError(f"invalid reviewed file list for {ticket.name}")
    return payload


def write_review_scope(
    project: Path,
    config: dict,
    ticket: Path,
    *,
    explicit_paths: list[str],
    discover: bool,
    allow_empty: bool,
) -> dict:
    paths = set(discovered_review_paths(project, config) if discover else [])
    paths.update(_safe_review_path(project, value) for value in explicit_paths)
    if not paths and not allow_empty:
        raise ValueError("review scope is empty; pass --allow-empty for a ticket-only review")
    payload = {
        "schema_version": 1,
        "ticket_id": ticket.name,
        "files": [_scope_entry(project, path) for path in sorted(paths)],
    }
    (ticket / REVIEW_SCOPE_FILE).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return payload


def change_fingerprint(project: Path, config: dict, ticket: Path) -> str:
    """Hash explicit reviewed files when frozen, otherwise the legacy worktree."""
    digest = hashlib.sha256()
    scope = load_review_scope(ticket)
    if scope is not None:
        digest.update(b"review-scope-v1\n")
        digest.update(json.dumps(scope, sort_keys=True, separators=(",", ":")).encode())
        for expected in sorted(scope["files"], key=lambda item: str(item["path"])):
            relative_name = _safe_review_path(project, str(expected["path"]))
            actual = _scope_entry(project, relative_name)
            digest.update(
                ("\nactual:" + json.dumps(actual, sort_keys=True, separators=(",", ":"))).encode()
            )
    else:
        base = git_output(project, ["rev-parse", "HEAD"]).strip() or "NO_GIT_HEAD"
        digest.update(f"base:{base}\n".encode())
        exclusions = workflow_exclusions(config)
        diff = git_output(project, ["diff", "--no-ext-diff", "--", ".", *exclusions])
        digest.update("\n".join(line.rstrip() for line in diff.splitlines()).encode())
        untracked = git_output(
            project,
            ["ls-files", "--others", "--exclude-standard", "--", ".", *exclusions],
        )
        for relative_name in sorted(line.strip() for line in untracked.splitlines() if line.strip()):
            untracked_path = project / relative_name
            if untracked_path.is_file():
                digest.update(f"\nuntracked:{relative_name.replace(chr(92), '/')}\n".encode())
                digest.update(untracked_path.read_bytes())
    for path in sorted(ticket.rglob("*")):
        if not path.is_file() or path.name.endswith(".pyc") or path.name == REVIEW_SCOPE_FILE:
            continue
        ticket_relative = path.relative_to(ticket).as_posix()
        if is_review_generated_artifact(config, ticket, ticket_relative):
            continue
        relative = path.relative_to(project) if path.is_relative_to(project) else path
        digest.update(f"\nfile:{relative.as_posix()}\n".encode())
        digest.update(normalized_file_text(path).encode())
    return digest.hexdigest()


def command_review_freeze(args: argparse.Namespace) -> int:
    config = load_config(args.project)
    ticket = ticket_dir(args.project, config, args.ticket)
    if not ticket.is_dir():
        print(f"Ticket not found: {ticket}", file=sys.stderr)
        return 2
    review = ticket / "review.md"
    review_text = review.read_text(encoding="utf-8", errors="replace") if review.exists() else ""
    if not re.search(r"\b(APPROVED|PASS)\b", review_text, re.IGNORECASE):
        print("Refusing review freeze: review has no APPROVED/PASS verdict", file=sys.stderr)
        return 1
    severity = review_has_unresolved_severity(review_text)
    if severity:
        print(f"Refusing review freeze: unresolved finding: {severity}", file=sys.stderr)
        return 1
    # Materialize every normalized lifecycle field before hashing. Commands
    # such as close and flow-link may update these values later, but must never
    # change the reviewed structure merely by inserting a previously absent
    # metadata line.
    readme = ticket / "README.md"
    metadata = parse_markdown_metadata(readme)
    defaults = {
        "Unlocks": "none",
        "Review status": "REVIEW READY",
        "Reviewed change fingerprint": "",
        "Status": "OPEN",
        "Done": "—",
        "Completed at": "",
    }
    for label in NORMALIZED_REVIEW_METADATA:
        key = label.lower().replace(" ", "_").replace("-", "_")
        write_metadata_field(readme, label, metadata.get(key, defaults[label]))
    if review.exists():
        write_metadata_field(review, "Change fingerprint", "")
    try:
        payload = write_review_scope(
            args.project,
            config,
            ticket,
            explicit_paths=list(args.path or []),
            discover=not args.no_discover,
            allow_empty=args.allow_empty,
        )
        fingerprint = change_fingerprint(args.project, config, ticket)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Refusing review freeze: {exc}", file=sys.stderr)
        return 2
    write_metadata_field(ticket / "README.md", "Reviewed change fingerprint", fingerprint)
    if review.exists():
        write_metadata_field(review, "Change fingerprint", fingerprint)
    if change_fingerprint(args.project, config, ticket) != fingerprint:
        print("Review fingerprint was not stable after metadata update", file=sys.stderr)
        return 2
    print(f"{ticket.name}: review scope frozen files={len(payload['files'])} fingerprint={fingerprint}")
    return 0


def review_has_unresolved_severity(review_text: str, severities: tuple[str, ...] = ("BLOCKER", "HIGH")) -> str | None:
    for line in review_text.splitlines():
        upper = line.upper()
        if any(re.search(rf"\b{severity}\b", upper) for severity in severities):
            if not re.search(r"\b(RESOLVED|FIXED|CLOSED)\b", upper):
                return line.strip()
    return None


def review_state(project: Path, config: dict, ticket: Path) -> dict[str, str | bool]:
    readme = ticket / "README.md"
    review = ticket / "review.md"
    metadata = parse_markdown_metadata(readme)
    scope_frozen = (ticket / REVIEW_SCOPE_FILE).is_file()
    current = change_fingerprint(project, config, ticket)
    displayed_current = current if scope_frozen else "LEGACY-SCOPE-NOT-FROZEN"
    reviewed = metadata.get("reviewed_change_fingerprint", "")
    if review.exists():
        review_text = review.read_text(encoding="utf-8", errors="replace")
    else:
        review_text = ""
    approved = bool(re.search(r"\b(APPROVED|PASS)\b", review_text, re.IGNORECASE))
    final_decision = "APPROVED" if approved else "PENDING"
    severity = review_has_unresolved_severity(review_text)
    stale = bool(approved and reviewed and (not scope_frozen or reviewed != current))
    if not review.exists():
        debt_reason = "review.md is missing"
    elif not approved:
        debt_reason = "review has no final APPROVED/PASS decision"
    elif severity:
        debt_reason = f"unresolved review finding: {severity}"
    elif not reviewed:
        debt_reason = "reviewed change fingerprint is missing"
    elif not scope_frozen:
        debt_reason = "legacy review scope is not frozen"
    elif stale:
        debt_reason = "review fingerprint differs from current change fingerprint"
    elif (ticket / "diff-note.md").exists() and placeholder_found((ticket / "diff-note.md").read_text(encoding="utf-8")):
        debt_reason = "acceptance evidence is incomplete"
    else:
        debt_reason = ""
    return {
        "approved": approved and not stale and not severity and not debt_reason,
        "decision": final_decision,
        "severity": "HIGH" if severity else ("STALE" if stale else ("MISSING" if debt_reason else "NONE")),
        "reason": debt_reason,
        "current_fingerprint": displayed_current,
        "reviewed_fingerprint": reviewed,
        "review_status": "REVIEW STALE" if stale else ("REVIEW APPROVED" if approved and not debt_reason else "REVIEW READY"),
    }


def validate_dependencies(project: Path, config: dict, flow_id: str) -> list[str]:
    errors: list[str] = []
    linked = {path.name: path for path in linked_tickets(project, config, flow_id)}
    graph: dict[str, list[str]] = {}
    for ticket_id, path in linked.items():
        deps = csv_values(parse_markdown_metadata(path / "README.md").get("dependencies"))
        graph[ticket_id] = deps
        for dep in deps:
            dep_path = ticket_dir(project, config, dep)
            if not dep_path.is_dir():
                errors.append(f"{ticket_id} depends on missing ticket {dep}")
            if dep == ticket_id:
                errors.append(f"{ticket_id} has a self-dependency")
            dep_meta = parse_markdown_metadata(dep_path / "README.md") if dep_path.is_dir() else {}
            dep_flow = (dep_meta.get("flow_id") or "").strip()
            if dep_path.is_dir() and dep_flow.lower() not in {"", "none"} and dep_flow != flow_id:
                errors.append(f"{ticket_id} depends on {dep} from unrelated flow {dep_meta.get('flow_id')}")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, stack: list[str]) -> None:
        if node in visiting:
            errors.append("circular dependency: " + " -> ".join([*stack, node]))
            return
        if node in visited or node not in graph:
            return
        visiting.add(node)
        for child in graph[node]:
            visit(child, [*stack, node])
        visiting.remove(node)
        visited.add(node)

    for ticket_id in graph:
        visit(ticket_id, [])
    return sorted(set(errors))


def ticket_blocker_reason(project: Path, config: dict, ticket: Path, flow_id: str) -> str:
    status = ticket_status(ticket)
    metadata = parse_markdown_metadata(ticket / "README.md")
    if status in {"DONE", "CANCELLED", "DEFERRED"}:
        return f"terminal status {status}"
    statuses = list(config["statuses"])
    if status not in statuses or statuses.index(status) < statuses.index("SPEC-READY"):
        return f"specification is not ready: {status}"
    blockers = metadata.get("blockers", "")
    if blockers and blockers.lower() not in {"none", "-"}:
        return f"unresolved blocker: {blockers}"
    for dep in csv_values(metadata.get("dependencies")):
        dep_status = ticket_status(ticket_dir(project, config, dep))
        if dep_status != "DONE":
            return f"dependency {dep} is {dep_status}, not DONE"
        dep_review = review_state(project, config, ticket_dir(project, config, dep))
        if dep_review["reason"]:
            return f"dependency {dep} has review debt: {dep_review['reason']}"
    return ""


def flow_model(project: Path, config: dict, flow_id: str) -> dict:
    tickets = linked_tickets(project, config, flow_id)
    rows = []
    for ticket in tickets:
        metadata = parse_markdown_metadata(ticket / "README.md")
        review = review_state(project, config, ticket)
        blocker = ticket_blocker_reason(project, config, ticket, flow_id)
        rows.append(
            {
                "id": ticket.name,
                "title": ticket_title(ticket),
                "status": ticket_status(ticket),
                "milestone": metadata.get("milestone_id", ""),
                "required": metadata.get("required_for_flow", "true").lower() != "false",
                "dependencies": csv_values(metadata.get("dependencies")),
                "unlocks": [],
                "priority": metadata.get("execution_order", metadata.get("priority", "")),
                "review": review,
                "blocker": blocker,
            }
        )
    by_id = {row["id"]: row for row in rows}
    for row in rows:
        for dep in row["dependencies"]:
            if dep in by_id:
                by_id[dep]["unlocks"].append(row["id"])
    def sort_key(row: dict) -> tuple[str, str]:
        return (str(row["priority"]).zfill(12), row["id"])
    rows.sort(key=sort_key)
    categories = {
        "in_progress": [row for row in rows if row["status"] == "IN-PROGRESS"],
        "waiting_review": [row for row in rows if row["status"] == "IN-REVIEW" and not row["review"]["reason"]],
        "changes_requested": [row for row in rows if row["review"]["severity"] in {"HIGH", "BLOCKER"}],
        "blocked": [row for row in rows if row["blocker"]],
        "next_executable": [row for row in rows if not row["blocker"] and row["status"] not in {"DONE", "IN-PROGRESS", "IN-REVIEW"}],
        "completed": [row for row in rows if row["status"] == "DONE"],
        "review_debt": [row for row in rows if row["review"]["reason"]],
    }
    return {"tickets": rows, "categories": categories, "dependency_errors": validate_dependencies(project, config, flow_id)}


def markdown_table(rows: list[dict], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return "_none_\n"
    header = "| " + " | ".join(title for title, _ in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(key, "")).replace("\n", " ") for _, key in columns) + " |")
    return "\n".join([header, sep, *body]) + "\n"


def generated_current_wave(model: dict) -> str:
    out = ["# Current Wave", "", "<!-- GENERATED: flow-sync; do not edit between generated markers -->", ""]
    sections = [
        ("IN PROGRESS", "in_progress"),
        ("WAITING FOR REVIEW", "waiting_review"),
        ("CHANGES REQUESTED", "changes_requested"),
        ("BLOCKED", "blocked"),
        ("NEXT EXECUTABLE", "next_executable"),
        ("RECENTLY COMPLETED", "completed"),
    ]
    for title, key in sections:
        rows = [
            {"id": row["id"], "status": row["status"], "reason": row["blocker"] or "executable", "unlocks": ", ".join(row["unlocks"]) or "none"}
            for row in model["categories"][key]
        ]
        out.extend([f"## {title}", "", markdown_table(rows, [("Ticket", "id"), ("Status", "status"), ("Reason", "reason"), ("Unlocks", "unlocks")]), ""])
    return "\n".join(out).rstrip() + "\n"


def generated_review_queue(model: dict) -> str:
    out = ["# Review Queue", "", "<!-- GENERATED: flow-sync; do not edit between generated markers -->", ""]
    sections = [
        ("MUST REVIEW", lambda row: row["review"]["severity"] == "MISSING"),
        ("RE-REVIEW REQUIRED", lambda row: row["review"]["severity"] == "STALE"),
        ("CHANGES REQUESTED", lambda row: row["review"]["severity"] == "HIGH"),
        ("BLOCKED BY REVIEW FINDINGS", lambda row: bool(row["review"]["reason"]) and row["review"]["severity"] not in {"MISSING", "STALE", "HIGH"}),
    ]
    for title, predicate in sections:
        rows = []
        for row in model["tickets"]:
            if predicate(row):
                rows.append(
                    {
                        "id": row["id"],
                        "reason": row["review"]["reason"],
                        "severity": row["review"]["severity"],
                        "previous": row["review"]["reviewed_fingerprint"] or "none",
                        "fingerprint": row["review"]["current_fingerprint"],
                        "action": "complete independent review and store matching fingerprint",
                    }
                )
        out.extend([f"## {title}", "", markdown_table(rows, [("Ticket", "id"), ("Reason", "reason"), ("Severity", "severity"), ("Previous review state", "previous"), ("Current fingerprint", "fingerprint"), ("Required next action", "action")]), ""])
    return "\n".join(out).rstrip() + "\n"


def update_flow_file(project: Path, config: dict, flow_id: str, model: dict) -> None:
    path = flow_dir(project, config, flow_id) / "flow.md"
    text = path.read_text(encoding="utf-8")
    required = [row for row in model["tickets"] if row["required"]]
    completed = model["categories"]["completed"]
    counts = {
        "updated_at": date.today().isoformat(),
        "required_ticket_count": str(len(required)),
        "completed_ticket_count": str(len([row for row in completed if row["required"]])),
        "active_ticket_count": str(len(model["categories"]["in_progress"])),
        "review_debt_count": str(len(model["categories"]["review_debt"])),
        "blocked_ticket_count": str(len(model["categories"]["blocked"]) + len(model["dependency_errors"])),
    }
    for key, value in counts.items():
        label = key.replace("_", " ")
        label = " ".join(part.capitalize() for part in label.split())
        text = re.sub(
            rf"^(\*\*{re.escape(label)}:\*\*)[ \t]*.*$",
            rf"\1 {value}",
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )
    generated = [
        "<!-- FLOW_SYNC_GENERATED_START -->",
        "## Ticket Dependency Graph",
        markdown_table(
            [{"id": row["id"], "deps": ", ".join(row["dependencies"]) or "none", "unlocks": ", ".join(row["unlocks"]) or "none"} for row in model["tickets"]],
            [("Ticket", "id"), ("Dependencies", "deps"), ("Unlocks", "unlocks")],
        ),
        "## Active Queue",
        markdown_table(
            [{"id": row["id"], "status": row["status"], "reason": row["blocker"] or "ready"} for row in model["tickets"] if row["status"] != "DONE"],
            [("Ticket", "id"), ("Status", "status"), ("Reason", "reason")],
        ),
        "## Completed Tickets",
        markdown_table(
            [{"id": row["id"], "unlocks": ", ".join(row["unlocks"]) or "none"} for row in completed],
            [("Ticket", "id"), ("Unlocks", "unlocks")],
        ),
        "<!-- FLOW_SYNC_GENERATED_END -->",
    ]
    replacement = "\n".join(generated)
    text, count = re.subn(
        r"<!-- FLOW_SYNC_GENERATED_START -->.*?<!-- FLOW_SYNC_GENERATED_END -->",
        replacement,
        text,
        flags=re.DOTALL,
    )
    if count == 0:
        text = text.rstrip() + "\n\n" + replacement + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def update_index(project: Path, config: dict) -> None:
    index = issue_path(project, config) / "README.md"
    if not index.exists():
        return
    update_next_marker(project, config)
    text = index.read_text(encoding="utf-8")
    flow_rows = [{"flow": flow.name, "status": parse_markdown_metadata(flow / "flow.md").get("status", "UNKNOWN")} for flow in flow_dirs(project, config)]
    block = "<!-- FLOW_INDEX -->\n## Flow index\n\n" + markdown_table(flow_rows, [("Flow", "flow"), ("Status", "status")]) + "<!-- /FLOW_INDEX -->"
    text, count = re.subn(r"<!-- FLOW_INDEX -->.*?<!-- /FLOW_INDEX -->", block, text, flags=re.DOTALL)
    if count == 0:
        text = text.rstrip() + "\n\n" + block + "\n"
    index.write_text(text, encoding="utf-8", newline="\n")


def command_flow_new(args: argparse.Namespace) -> int:
    config = load_config(args.project)
    template = flow_path(args.project, config) / "_TEMPLATE"
    if not template.is_dir():
        print(f"Missing flow template directory: {template}", file=sys.stderr)
        return 2
    flow_id = next_flow_id(args.project, config)
    target = flow_dir(args.project, config, flow_id)
    target.mkdir(parents=False, exist_ok=False)
    created = args.created or date.today().isoformat()
    for source in template.iterdir():
        if source.is_file():
            text = replace_flow_tokens(source.read_text(encoding="utf-8"), flow_id, args.title, created)
            (target / source.name).write_text(text, encoding="utf-8", newline="\n")
    update_index(args.project, config)
    print(target)
    return 0


def command_flow_link(args: argparse.Namespace) -> int:
    config = load_config(args.project)
    flow = flow_dir(args.project, config, args.flow)
    ticket = ticket_dir(args.project, config, args.ticket)
    if not flow.is_dir():
        print(f"Flow not found: {flow}", file=sys.stderr)
        return 2
    if not ticket.is_dir():
        print(f"Ticket not found: {ticket}", file=sys.stderr)
        return 2
    deps = csv_values(args.depends_on)
    if args.ticket in deps:
        print(f"Self-dependency is not allowed: {args.ticket}", file=sys.stderr)
        return 2
    for dep in deps:
        if not ticket_dir(args.project, config, dep).is_dir():
            print(f"Dependency ticket not found: {dep}", file=sys.stderr)
            return 2
    readme = ticket / "README.md"
    original_readme = readme.read_text(encoding="utf-8")
    existing = parse_markdown_metadata(readme).get("flow_id")
    if existing and existing.lower() != "none" and existing != args.flow:
        print(f"Ticket already linked to {existing}; refusing silent reassignment.", file=sys.stderr)
        return 2
    write_metadata_field(readme, "Flow ID", args.flow)
    write_metadata_field(readme, "Milestone ID", args.milestone)
    write_metadata_field(readme, "Required for flow", "true" if args.required else "false")
    write_metadata_field(readme, "Dependencies", ", ".join(deps) if deps else "none")
    write_metadata_field(readme, "Execution order", str(args.execution_order or ""))
    write_metadata_field(readme, "Review status", parse_markdown_metadata(readme).get("review_status", "REVIEW READY"))
    write_metadata_field(readme, "Reviewed change fingerprint", parse_markdown_metadata(readme).get("reviewed_change_fingerprint", ""))
    errors = validate_dependencies(args.project, config, args.flow)
    if errors:
        readme.write_text(original_readme, encoding="utf-8", newline="\n")
        for error in errors:
            print(error, file=sys.stderr)
        return 2
    command_flow_sync(argparse.Namespace(project=args.project, flow=args.flow))
    print(f"{args.ticket} linked to {args.flow}")
    return 0


def command_flow_sync(args: argparse.Namespace) -> int:
    config = load_config(args.project)
    flow = flow_dir(args.project, config, args.flow)
    if not flow.is_dir():
        print(f"Flow not found: {flow}", file=sys.stderr)
        return 2
    model = flow_model(args.project, config, args.flow)
    if model["dependency_errors"]:
        for error in model["dependency_errors"]:
            print(error, file=sys.stderr)
        return 2
    for row in model["tickets"]:
        readme = ticket_dir(args.project, config, row["id"]) / "README.md"
        write_metadata_field(readme, "Unlocks", ", ".join(row["unlocks"]) if row["unlocks"] else "none")
        write_metadata_field(readme, "Review status", str(row["review"]["review_status"]))
    (flow / "current-wave.md").write_text(generated_current_wave(model), encoding="utf-8", newline="\n")
    (flow / "review-queue.md").write_text(generated_review_queue(model), encoding="utf-8", newline="\n")
    update_flow_file(args.project, config, args.flow, model)
    update_index(args.project, config)
    print(f"Synchronized {args.flow}: tickets={len(model['tickets'])}")
    return 0


def command_review_queue(args: argparse.Namespace) -> int:
    return command_flow_sync(args)


def flow_status_report(project: Path, config: dict, flow_id: str) -> dict:
    flow_meta = parse_markdown_metadata(flow_dir(project, config, flow_id) / "flow.md")
    model = flow_model(project, config, flow_id)
    return {
        "flow_id": flow_id,
        "final_outcome": flow_meta.get("final_outcome", ""),
        "status": flow_meta.get("status", "UNKNOWN"),
        "current_milestone": flow_meta.get("current_milestone", ""),
        "progress": f"{len([r for r in model['categories']['completed'] if r['required']])}/{len([r for r in model['tickets'] if r['required']])}",
        "active_tickets": [row["id"] for row in model["categories"]["in_progress"]],
        "waiting_for_review": [row["id"] for row in model["categories"]["waiting_review"]],
        "stale_reviews": [row["id"] for row in model["categories"]["review_debt"] if row["review"]["severity"] == "STALE"],
        "blocked": [{"ticket": row["id"], "reason": row["blocker"]} for row in model["categories"]["blocked"]],
        "next_executable": [{"ticket": row["id"], "reason": "all required dependencies and spec gates are satisfied"} for row in model["categories"]["next_executable"]],
        "recently_completed": [row["id"] for row in model["categories"]["completed"]],
        "missing_closeout_evidence": flow_close_errors(project, config, flow_id),
    }


def command_flow_status(args: argparse.Namespace) -> int:
    config = load_config(args.project)
    report = flow_status_report(args.project, config, args.flow)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    for key, value in report.items():
        print(console_safe_text(f"{key}: {value}"))
    return 0


def console_safe_text(value: str, encoding: str | None = None) -> str:
    """Return printable text without crashing on a narrow Windows code page."""
    target_encoding = encoding or getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        value.encode(target_encoding)
        return value
    except (LookupError, UnicodeEncodeError):
        return value.encode(target_encoding, errors="backslashreplace").decode(target_encoding)


def command_flow_audit(args: argparse.Namespace) -> int:
    config = load_config(args.project)
    errors = validate_dependencies(args.project, config, args.flow) + flow_close_errors(args.project, config, args.flow, require_done=False)
    if errors:
        print(f"FAIL {args.flow}")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"PASS {args.flow}")
    return 0


def flow_close_errors(project: Path, config: dict, flow_id: str, *, require_done: bool = True) -> list[str]:
    errors: list[str] = []
    flow = flow_dir(project, config, flow_id)
    if not flow.is_dir():
        return [f"flow not found: {flow_id}"]
    model = flow_model(project, config, flow_id)
    errors.extend(model["dependency_errors"])
    for row in model["tickets"]:
        if row["required"] and row["status"] != "DONE":
            errors.append(f"required ticket {row['id']} is {row['status']}, not DONE")
        if row["required"] and row["review"]["reason"]:
            errors.append(f"required ticket {row['id']} has review debt: {row['review']['reason']}")
    closeout = flow / "closeout.md"
    if require_done and closeout.exists():
        text = closeout.read_text(encoding="utf-8")
        if placeholder_found(text) or not re.search(r"\b(APPROVED|PASS|DONE)\b", text, re.IGNORECASE):
            errors.append("flow closeout.md lacks final evidence and approval decision")
    elif require_done:
        errors.append("flow closeout.md is missing")
    return sorted(set(errors))


def command_flow_close(args: argparse.Namespace) -> int:
    config = load_config(args.project)
    sync_code = command_flow_sync(argparse.Namespace(project=args.project, flow=args.flow))
    if sync_code:
        return sync_code
    errors = flow_close_errors(args.project, config, args.flow)
    if errors:
        print("Refusing FLOW DONE:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    flow_md = flow_dir(args.project, config, args.flow) / "flow.md"
    write_metadata_field(flow_md, "Status", "DONE")
    write_metadata_field(flow_md, "Updated at", date.today().isoformat())
    print(f"{args.flow}: DONE")
    return 0


def close_ticket_errors(project: Path, config: dict, ticket: Path) -> list[str]:
    errors = audit_ticket(ticket, config, closeout=True)
    state = review_state(project, config, ticket)
    if state["reason"]:
        errors.append(f"review debt: {state['reason']}")
    review_text = (ticket / "review.md").read_text(encoding="utf-8", errors="replace") if (ticket / "review.md").exists() else ""
    severity = review_has_unresolved_severity(review_text)
    if severity:
        errors.append(f"unresolved BLOCKER/HIGH review finding: {severity}")
    return sorted(set(errors))


def command_close(args: argparse.Namespace) -> int:
    config = load_config(args.project)
    ticket = ticket_dir(args.project, config, args.ticket)
    if not ticket.is_dir():
        print(f"Ticket not found: {ticket}", file=sys.stderr)
        return 2
    errors = close_ticket_errors(args.project, config, ticket)
    if errors:
        print("Refusing DONE:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    readme = ticket / "README.md"
    write_metadata_field(readme, "Status", "DONE")
    write_metadata_field(readme, "Done", date.today().isoformat())
    write_metadata_field(readme, "Completed at", date.today().isoformat())
    metadata = parse_markdown_metadata(readme)
    flow_id = metadata.get("flow_id")
    if flow_id and flow_id.lower() != "none":
        command_flow_sync(argparse.Namespace(project=args.project, flow=flow_id))
    print(f"{args.ticket}: DONE")
    return 0


def selected_tickets(args: argparse.Namespace, config: dict) -> list[Path]:
    if not getattr(args, "ticket", None):
        return ticket_dirs(args.project, config)
    path = issue_path(args.project, config) / args.ticket
    if not path.is_dir() or not ticket_pattern(config).fullmatch(args.ticket):
        raise ValueError(f"ticket does not exist or has invalid ID: {args.ticket}")
    return [path]


def command_audit(args: argparse.Namespace) -> int:
    config = load_config(args.project)
    try:
        tickets = selected_tickets(args, config)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    failures = 0
    for ticket in tickets:
        errors = audit_ticket(ticket, config)
        if errors:
            failures += 1
            print(f"FAIL {ticket.name}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {ticket.name}")
    if not tickets:
        print("No ticket directories found.", file=sys.stderr)
        return 2
    print(f"Audited {len(tickets)} ticket(s); failures={failures}")
    return 1 if failures else 0


def command_status(args: argparse.Namespace) -> int:
    config = load_config(args.project)
    statuses = list(config["statuses"])
    target_path = issue_path(args.project, config) / args.ticket
    if not target_path.is_dir():
        print(f"Ticket not found: {target_path}", file=sys.stderr)
        return 2
    readme = target_path / "README.md"
    current = parse_status(readme)
    if current not in statuses or args.to not in statuses:
        print(f"Invalid transition: {current!r} -> {args.to!r}", file=sys.stderr)
        return 2
    current_index = statuses.index(current)
    target_index = statuses.index(args.to)
    if target_index != current_index + 1:
        print(
            f"Only the next lifecycle transition is allowed: {current} -> "
            f"{statuses[current_index + 1] if current_index + 1 < len(statuses) else 'none'}",
            file=sys.stderr,
        )
        return 2
    if args.to == "DONE":
        errors = close_ticket_errors(args.project, {**config, "statuses": statuses}, target_path)
        if errors:
            print("Refusing DONE:", file=sys.stderr)
            for error in sorted(set(errors)):
                print(f"  - {error}", file=sys.stderr)
            return 1
    text = readme.read_text(encoding="utf-8")
    text, count = re.subn(
        r"^(\*\*Status:\*\*)[ \t]*[A-Z][A-Z-]*[ \t]*$",
        rf"\1 {args.to}",
        text,
        flags=re.MULTILINE,
    )
    if count != 1:
        print("Could not update exactly one Status field.", file=sys.stderr)
        return 2
    if args.to == "DONE":
        text = re.sub(
            r"^(\*\*Done:\*\*)[ \t]*.*$",
            rf"\1 {date.today().isoformat()}",
            text,
            flags=re.MULTILINE,
        )
    readme.write_text(text, encoding="utf-8", newline="\n")
    print(f"{args.ticket}: {current} -> {args.to}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="install the starter workflow")
    init.add_argument("--project", required=True, type=project_path)
    init.add_argument(
        "--merge",
        action="store_true",
        help="copy missing files only; never overwrite existing files",
    )
    init.set_defaults(func=command_init)

    new = sub.add_parser("new", help="create the next ticket")
    new.add_argument("--project", required=True, type=project_path)
    new.add_argument("--title", required=True)
    new.add_argument("--opened", help="YYYY-MM-DD; defaults to today")
    new.set_defaults(func=command_new)

    audit = sub.add_parser("audit", help="audit ticket structure and DONE gates")
    audit.add_argument("--project", required=True, type=project_path)
    audit.add_argument("--ticket")
    audit.set_defaults(func=command_audit)

    status = sub.add_parser("status", help="move one lifecycle step")
    status.add_argument("--project", required=True, type=project_path)
    status.add_argument("--ticket", required=True)
    status.add_argument("--to", required=True)
    status.set_defaults(func=command_status)

    close = sub.add_parser("close", help="run ticket closeout gates and mark DONE")
    close.add_argument("--project", required=True, type=project_path)
    close.add_argument("--ticket", required=True)
    close.set_defaults(func=command_close)

    review_freeze = sub.add_parser(
        "review-freeze",
        help="freeze explicit reviewed-file hashes and store a stable fingerprint",
    )
    review_freeze.add_argument("--project", required=True, type=project_path)
    review_freeze.add_argument("--ticket", required=True)
    review_freeze.add_argument(
        "--path",
        action="append",
        default=[],
        help="project-relative reviewed file; repeat for post-commit or selected scope",
    )
    review_freeze.add_argument(
        "--no-discover",
        action="store_true",
        help="do not include current non-workflow Git changes automatically",
    )
    review_freeze.add_argument(
        "--allow-empty",
        action="store_true",
        help="allow ticket-evidence-only review with no product files",
    )
    review_freeze.set_defaults(func=command_review_freeze)

    flow_new = sub.add_parser("flow-new", help="create the next Flow")
    flow_new.add_argument("--project", required=True, type=project_path)
    flow_new.add_argument("--title", required=True)
    flow_new.add_argument("--created", help="YYYY-MM-DD; defaults to today")
    flow_new.set_defaults(func=command_flow_new)

    flow_link = sub.add_parser("flow-link", help="link a ticket to a Flow")
    flow_link.add_argument("--project", required=True, type=project_path)
    flow_link.add_argument("--flow", required=True)
    flow_link.add_argument("--ticket", required=True)
    flow_link.add_argument("--milestone", required=True)
    flow_link.add_argument("--depends-on", default="")
    flow_link.add_argument("--execution-order")
    flow_link.add_argument("--optional", dest="required", action="store_false")
    flow_link.set_defaults(required=True, func=command_flow_link)

    flow_status = sub.add_parser("flow-status", help="show Flow operational status")
    flow_status.add_argument("--project", required=True, type=project_path)
    flow_status.add_argument("--flow", required=True)
    flow_status.add_argument("--json", action="store_true")
    flow_status.set_defaults(func=command_flow_status)

    flow_sync = sub.add_parser("flow-sync", help="regenerate deterministic Flow state")
    flow_sync.add_argument("--project", required=True, type=project_path)
    flow_sync.add_argument("--flow", required=True)
    flow_sync.set_defaults(func=command_flow_sync)

    review_queue = sub.add_parser("review-queue", help="regenerate and show Flow review queue")
    review_queue.add_argument("--project", required=True, type=project_path)
    review_queue.add_argument("--flow", required=True)
    review_queue.set_defaults(func=command_review_queue)

    flow_audit = sub.add_parser("flow-audit", help="audit Flow without marking DONE")
    flow_audit.add_argument("--project", required=True, type=project_path)
    flow_audit.add_argument("--flow", required=True)
    flow_audit.set_defaults(func=command_flow_audit)

    flow_close = sub.add_parser("flow-close", help="run Flow closeout gates and mark DONE")
    flow_close.add_argument("--project", required=True, type=project_path)
    flow_close.add_argument("--flow", required=True)
    flow_close.set_defaults(func=command_flow_close)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
