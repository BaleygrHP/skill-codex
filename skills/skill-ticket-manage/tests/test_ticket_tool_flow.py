import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
TOOL = SKILL_ROOT / "scripts" / "ticket_tool.py"
SPEC = importlib.util.spec_from_file_location("ticket_tool", TOOL)
ticket_tool = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ticket_tool)


class TicketToolFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / "project"
        self.project.mkdir()
        self.run_project_command("init")

    def tearDown(self):
        self.tmp.cleanup()

    def run_project_command(self, *args, check=True):
        result = subprocess.run(
            [sys.executable, str(TOOL), *args, "--project", str(self.project)]
            if args and args[0] in {"init", "new"}
            else [sys.executable, str(TOOL), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(f"command failed: {args}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def cmd(self, *args, check=True):
        result = subprocess.run(
            [sys.executable, str(TOOL), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(f"command failed: {args}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def git(self, *args):
        result = subprocess.run(
            ["git", *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            self.fail(f"git command failed: {args}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def new_ticket(self, title="Ticket"):
        return self.cmd("new", "--project", str(self.project), "--title", title).stdout.strip().splitlines()[-1]

    def new_flow(self, title="Flow"):
        return self.cmd("flow-new", "--project", str(self.project), "--title", title).stdout.strip().splitlines()[-1]

    def ticket_path(self, ticket_id):
        return self.project / "Issue" / ticket_id

    def flow_id_from_path(self, path):
        return Path(path).name

    def complete_ticket_artifacts(
        self, ticket_id, *, status="IN-REVIEW", severity=None, freeze=True
    ):
        ticket = self.ticket_path(ticket_id)
        readme = ticket / "README.md"
        text = readme.read_text(encoding="utf-8")
        text = text.replace("**Status:** OPEN", f"**Status:** {status}")
        text = text.replace("- [ ]", "- [x]")
        readme.write_text(text, encoding="utf-8", newline="\n")
        (ticket / "spec.md").write_text(
            f"# {ticket_id} - Spec\n\n## Acceptance Criteria\n\n| ID | Criterion | Verification |\n| --- | --- | --- |\n| AC1 | works | unit test pass |\n",
            encoding="utf-8",
            newline="\n",
        )
        (ticket / "diff-note.md").write_text(
            "# Diff Note\n\n## Tests run\n\n```text\nunit test pass\n```\n",
            encoding="utf-8",
            newline="\n",
        )
        finding = f"- {severity}: unresolved finding\n" if severity else "- none\n"
        (ticket / "review.md").write_text(
            f"# Review\n\n**Status:** APPROVED\n\n## Findings\n\n{finding}\n## Verdict\n\nAPPROVED\n",
            encoding="utf-8",
            newline="\n",
        )
        config = ticket_tool.load_config(self.project)
        if freeze and severity is None:
            ticket_tool.write_review_scope(
                self.project,
                config,
                ticket,
                explicit_paths=[],
                discover=True,
                allow_empty=True,
            )
        fp = ticket_tool.change_fingerprint(self.project, config, ticket)
        ticket_tool.write_metadata_field(readme, "Reviewed change fingerprint", fp)
        return fp

    def test_init_merge_adds_flow_without_overwriting(self):
        flow_template = self.project / "FLOW" / "_TEMPLATE" / "flow.md"
        original = flow_template.read_text(encoding="utf-8")
        flow_template.write_text("custom\n", encoding="utf-8", newline="\n")
        self.cmd("init", "--project", str(self.project), "--merge")
        self.assertEqual(flow_template.read_text(encoding="utf-8"), "custom\n")
        self.assertNotEqual(original, "custom\n")

    def test_flow_new_creates_deterministic_ids(self):
        first = self.flow_id_from_path(self.new_flow("A"))
        second = self.flow_id_from_path(self.new_flow("B"))
        self.assertEqual((first, second), ("FL000001", "FL000002"))

    def test_flow_link_valid_ticket_and_dependency_rejections(self):
        flow = self.flow_id_from_path(self.new_flow())
        t1 = Path(self.new_ticket("A")).name
        t2 = Path(self.new_ticket("B")).name
        self.cmd("flow-link", "--project", str(self.project), "--flow", flow, "--ticket", t1, "--milestone", "M1")
        self.assertIn("**Flow ID:** FL000001", (self.ticket_path(t1) / "README.md").read_text(encoding="utf-8"))
        missing = self.cmd("flow-link", "--project", str(self.project), "--flow", flow, "--ticket", t2, "--milestone", "M1", "--depends-on", "TD999999", check=False)
        self.assertNotEqual(missing.returncode, 0)
        self_dep = self.cmd("flow-link", "--project", str(self.project), "--flow", flow, "--ticket", t2, "--milestone", "M1", "--depends-on", t2, check=False)
        self.assertNotEqual(self_dep.returncode, 0)

    def test_circular_dependency_is_rejected(self):
        flow = self.flow_id_from_path(self.new_flow())
        t1 = Path(self.new_ticket("A")).name
        t2 = Path(self.new_ticket("B")).name
        self.cmd("flow-link", "--project", str(self.project), "--flow", flow, "--ticket", t1, "--milestone", "M1", "--depends-on", t2)
        circular = self.cmd("flow-link", "--project", str(self.project), "--flow", flow, "--ticket", t2, "--milestone", "M1", "--depends-on", t1, check=False)
        self.assertNotEqual(circular.returncode, 0)
        self.assertIn("circular dependency", circular.stderr)

    def test_flow_sync_is_idempotent_and_done_moves_to_completed_without_deleting_folder(self):
        flow = self.flow_id_from_path(self.new_flow())
        t1 = Path(self.new_ticket("A")).name
        self.cmd("flow-link", "--project", str(self.project), "--flow", flow, "--ticket", t1, "--milestone", "M1")
        self.complete_ticket_artifacts(t1, status="DONE")
        self.cmd("flow-sync", "--project", str(self.project), "--flow", flow)
        current_wave = self.project / "FLOW" / flow / "current-wave.md"
        first = current_wave.read_text(encoding="utf-8")
        self.cmd("flow-sync", "--project", str(self.project), "--flow", flow)
        self.assertEqual(first, current_wave.read_text(encoding="utf-8"))
        self.assertIn("RECENTLY COMPLETED", first)
        self.assertTrue(self.ticket_path(t1).is_dir())

    def test_missing_review_and_stale_review_create_review_debt(self):
        flow = self.flow_id_from_path(self.new_flow())
        t1 = Path(self.new_ticket("A")).name
        self.cmd("flow-link", "--project", str(self.project), "--flow", flow, "--ticket", t1, "--milestone", "M1")
        self.cmd("flow-sync", "--project", str(self.project), "--flow", flow)
        self.assertIn("review has no final", (self.project / "FLOW" / flow / "review-queue.md").read_text(encoding="utf-8"))
        self.complete_ticket_artifacts(t1, freeze=False)
        (self.ticket_path(t1) / "diff-note.md").write_text("# Diff Note\n\n## Tests run\n\n```text\nchanged\n```\n", encoding="utf-8", newline="\n")
        self.cmd("flow-sync", "--project", str(self.project), "--flow", flow)
        self.assertIn("RE-REVIEW REQUIRED", (self.project / "FLOW" / flow / "review-queue.md").read_text(encoding="utf-8"))

    def test_blocker_or_high_prevents_ticket_done(self):
        t1 = Path(self.new_ticket("A")).name
        self.complete_ticket_artifacts(t1, severity="HIGH")
        result = self.cmd("close", "--project", str(self.project), "--ticket", t1, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unresolved BLOCKER/HIGH", result.stderr)

    def test_matching_approved_review_permits_close_and_unlocks_dependent_ticket(self):
        flow = self.flow_id_from_path(self.new_flow())
        t1 = Path(self.new_ticket("A")).name
        t2 = Path(self.new_ticket("B")).name
        self.cmd("flow-link", "--project", str(self.project), "--flow", flow, "--ticket", t1, "--milestone", "M1")
        self.cmd("flow-link", "--project", str(self.project), "--flow", flow, "--ticket", t2, "--milestone", "M1", "--depends-on", t1)
        self.complete_ticket_artifacts(t1)
        self.cmd("close", "--project", str(self.project), "--ticket", t1)
        wave = (self.project / "FLOW" / flow / "current-wave.md").read_text(encoding="utf-8")
        queue = (self.project / "FLOW" / flow / "review-queue.md").read_text(encoding="utf-8")
        self.assertIn(t2, wave)
        self.assertIn("NEXT EXECUTABLE", wave)
        self.assertNotIn("review fingerprint differs", queue)

    def test_flow_close_gates_incomplete_ticket_review_debt_and_evidence(self):
        flow = self.flow_id_from_path(self.new_flow())
        t1 = Path(self.new_ticket("A")).name
        self.cmd("flow-link", "--project", str(self.project), "--flow", flow, "--ticket", t1, "--milestone", "M1")
        incomplete = self.cmd("flow-close", "--project", str(self.project), "--flow", flow, check=False)
        self.assertNotEqual(incomplete.returncode, 0)
        self.assertIn("required ticket", incomplete.stderr)
        readme = self.ticket_path(t1) / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8").replace("**Status:** OPEN", "**Status:** DONE"),
            encoding="utf-8",
            newline="\n",
        )
        review_debt = self.cmd("flow-close", "--project", str(self.project), "--flow", flow, check=False)
        self.assertNotEqual(review_debt.returncode, 0)
        self.assertIn("review debt", review_debt.stderr)
        self.complete_ticket_artifacts(t1, status="DONE")
        evidence = self.cmd("flow-close", "--project", str(self.project), "--flow", flow, check=False)
        self.assertNotEqual(evidence.returncode, 0)
        self.assertIn("closeout.md", evidence.stderr)

    def test_flow_close_succeeds_only_when_every_gate_passes_and_legacy_audit_still_works(self):
        flow = self.flow_id_from_path(self.new_flow())
        t1 = Path(self.new_ticket("A")).name
        legacy = Path(self.new_ticket("Standalone")).name
        self.cmd("flow-link", "--project", str(self.project), "--flow", flow, "--ticket", t1, "--milestone", "M1")
        self.complete_ticket_artifacts(t1, status="DONE")
        (self.project / "FLOW" / flow / "closeout.md").write_text("# Closeout\n\nFinal evidence PASS\n\nFinal Decision APPROVED\n", encoding="utf-8", newline="\n")
        result = self.cmd("flow-close", "--project", str(self.project), "--flow", flow)
        self.assertEqual(result.returncode, 0)
        audit = self.cmd("audit", "--project", str(self.project), "--ticket", legacy)
        self.assertIn(f"PASS {legacy}", audit.stdout)
        self.assertTrue(self.ticket_path(t1).is_dir())

    def test_uncommitted_worktree_fingerprinting_is_deterministic(self):
        self.git("init", str(self.project))
        self.git("-C", str(self.project), "config", "user.email", "tests@example.invalid")
        self.git("-C", str(self.project), "config", "user.name", "Ticket Tool Tests")
        self.git("-C", str(self.project), "add", ".")
        self.git("-C", str(self.project), "commit", "-m", "baseline")
        t1 = Path(self.new_ticket("A")).name
        source = self.project / "source.py"
        source.write_text("value = 1\n", encoding="utf-8", newline="\n")
        self.complete_ticket_artifacts(t1)
        config = ticket_tool.load_config(self.project)
        first = ticket_tool.change_fingerprint(self.project, config, self.ticket_path(t1))
        second = ticket_tool.change_fingerprint(self.project, config, self.ticket_path(t1))
        self.assertEqual(first, second)
        ticket_tool.write_metadata_field(self.ticket_path(t1) / "README.md", "Status", "DONE")
        ticket_tool.write_metadata_field(self.ticket_path(t1) / "README.md", "Review status", "REVIEW APPROVED")
        self.assertEqual(first, ticket_tool.change_fingerprint(self.project, config, self.ticket_path(t1)))
        source.write_text("value = 2\n", encoding="utf-8", newline="\n")
        self.assertNotEqual(first, ticket_tool.change_fingerprint(self.project, config, self.ticket_path(t1)))

    def test_reviewed_file_manifest_survives_commit_and_unrelated_change(self):
        self.git("init", str(self.project))
        self.git("-C", str(self.project), "config", "user.email", "tests@example.invalid")
        self.git("-C", str(self.project), "config", "user.name", "Ticket Tool Tests")
        self.git("-C", str(self.project), "add", ".")
        self.git("-C", str(self.project), "commit", "-m", "baseline")
        t1 = Path(self.new_ticket("Scoped review")).name
        source = self.project / "source.py"
        source.write_text("value = 1\n", encoding="utf-8", newline="\n")
        self.complete_ticket_artifacts(t1)

        self.cmd("review-freeze", "--project", str(self.project), "--ticket", t1)
        config = ticket_tool.load_config(self.project)
        ticket = self.ticket_path(t1)
        frozen = ticket_tool.change_fingerprint(self.project, config, ticket)
        self.assertTrue(ticket_tool.review_state(self.project, config, ticket)["approved"])

        self.git("-C", str(self.project), "add", ".")
        self.git("-C", str(self.project), "commit", "-m", "approved change")
        self.assertEqual(frozen, ticket_tool.change_fingerprint(self.project, config, ticket))
        self.assertTrue(ticket_tool.review_state(self.project, config, ticket)["approved"])

        unrelated = self.project / "unrelated.py"
        unrelated.write_text("other = 1\n", encoding="utf-8", newline="\n")
        self.git("-C", str(self.project), "add", "unrelated.py")
        self.git("-C", str(self.project), "commit", "-m", "unrelated change")
        self.assertEqual(frozen, ticket_tool.change_fingerprint(self.project, config, ticket))
        self.assertTrue(ticket_tool.review_state(self.project, config, ticket)["approved"])

        source.write_text("value = 2\n", encoding="utf-8", newline="\n")
        self.assertNotEqual(frozen, ticket_tool.change_fingerprint(self.project, config, ticket))
        self.assertFalse(ticket_tool.review_state(self.project, config, ticket)["approved"])

    def test_legacy_review_queue_uses_stable_migration_sentinel_across_commits(self):
        self.git("init", str(self.project))
        self.git("-C", str(self.project), "config", "user.email", "tests@example.invalid")
        self.git("-C", str(self.project), "config", "user.name", "Ticket Tool Tests")
        self.git("-C", str(self.project), "add", ".")
        self.git("-C", str(self.project), "commit", "-m", "baseline")
        flow = self.flow_id_from_path(self.new_flow("Legacy flow"))
        ticket_id = Path(self.new_ticket("Legacy review")).name
        self.cmd(
            "flow-link",
            "--project",
            str(self.project),
            "--flow",
            flow,
            "--ticket",
            ticket_id,
            "--milestone",
            "M1",
        )
        self.complete_ticket_artifacts(ticket_id, freeze=False)
        self.cmd("flow-sync", "--project", str(self.project), "--flow", flow)
        queue = self.project / "FLOW" / flow / "review-queue.md"
        before = queue.read_text(encoding="utf-8")
        self.assertIn("LEGACY-SCOPE-NOT-FROZEN", before)

        self.git("-C", str(self.project), "add", ".")
        self.git("-C", str(self.project), "commit", "-m", "legacy review state")
        unrelated = self.project / "unrelated.py"
        unrelated.write_text("unrelated = True\n", encoding="utf-8", newline="\n")
        self.git("-C", str(self.project), "add", "unrelated.py")
        self.git("-C", str(self.project), "commit", "-m", "unrelated")
        self.cmd("flow-sync", "--project", str(self.project), "--flow", flow)
        self.assertEqual(before, queue.read_text(encoding="utf-8"))

    def test_review_scope_tracks_added_deleted_and_explicit_historical_files(self):
        self.git("init", str(self.project))
        self.git("-C", str(self.project), "config", "user.email", "tests@example.invalid")
        self.git("-C", str(self.project), "config", "user.name", "Ticket Tool Tests")
        old = self.project / "old.py"
        old.write_text("old = True\n", encoding="utf-8", newline="\n")
        self.git("-C", str(self.project), "add", ".")
        self.git("-C", str(self.project), "commit", "-m", "baseline")
        t1 = Path(self.new_ticket("Add delete")).name
        old.unlink()
        new = self.project / "new.py"
        new.write_text("new = True\n", encoding="utf-8", newline="\n")
        self.complete_ticket_artifacts(t1)

        self.cmd("review-freeze", "--project", str(self.project), "--ticket", t1)
        manifest = json.loads(
            (self.ticket_path(t1) / "reviewed-files.json").read_text(encoding="utf-8")
        )
        entries = {item["path"]: item for item in manifest["files"]}
        self.assertEqual(entries["old.py"]["expected"], "absent")
        self.assertEqual(entries["new.py"]["expected"], "present")
        self.assertTrue(entries["new.py"]["sha256"])

        self.git("-C", str(self.project), "add", ".")
        self.git("-C", str(self.project), "commit", "-m", "migration")
        historical = Path(self.new_ticket("Historical")).name
        self.complete_ticket_artifacts(historical)
        self.cmd(
            "review-freeze",
            "--project",
            str(self.project),
            "--ticket",
            historical,
            "--no-discover",
            "--path",
            "new.py",
        )
        historical_manifest = json.loads(
            (self.ticket_path(historical) / "reviewed-files.json").read_text(encoding="utf-8")
        )
        self.assertEqual([item["path"] for item in historical_manifest["files"]], ["new.py"])

        governed = f"Issue/{t1}/README.md"
        self.cmd(
            "review-freeze",
            "--project",
            str(self.project),
            "--ticket",
            historical,
            "--no-discover",
            "--path",
            governed,
        )
        governed_manifest = json.loads(
            (self.ticket_path(historical) / "reviewed-files.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            [item["path"] for item in governed_manifest["files"]],
            [governed],
        )
        config = ticket_tool.load_config(self.project)
        historical_ticket = self.ticket_path(historical)
        governed_fingerprint = ticket_tool.change_fingerprint(
            self.project, config, historical_ticket
        )
        governed_readme = self.ticket_path(t1) / "README.md"
        ticket_tool.write_metadata_field(governed_readme, "Review status", "REVIEW STALE")
        ticket_tool.write_metadata_field(governed_readme, "Unlocks", "TD999999")
        self.assertEqual(
            governed_fingerprint,
            ticket_tool.change_fingerprint(self.project, config, historical_ticket),
        )
        governed_readme.write_text(
            governed_readme.read_text(encoding="utf-8") + "\nmaterial evidence changed\n",
            encoding="utf-8",
            newline="\n",
        )
        self.assertNotEqual(
            governed_fingerprint,
            ticket_tool.change_fingerprint(self.project, config, historical_ticket),
        )

    def test_review_scope_preserves_dot_directory_paths(self):
        self.git("init", str(self.project))
        self.git("-C", str(self.project), "config", "user.email", "tests@example.invalid")
        self.git("-C", str(self.project), "config", "user.name", "Ticket Tool Tests")
        self.git("-C", str(self.project), "add", ".")
        self.git("-C", str(self.project), "commit", "-m", "baseline")
        ticket_id = Path(self.new_ticket("Dot path")).name
        dot_file = self.project / ".github" / "workflow.yml"
        dot_file.parent.mkdir()
        dot_file.write_text("name: test\n", encoding="utf-8", newline="\n")
        self.complete_ticket_artifacts(ticket_id)

        self.cmd("review-freeze", "--project", str(self.project), "--ticket", ticket_id)
        manifest = json.loads(
            (self.ticket_path(ticket_id) / "reviewed-files.json").read_text(encoding="utf-8")
        )
        self.assertEqual([item["path"] for item in manifest["files"]], [".github/workflow.yml"])

    def test_review_fingerprint_survives_close_and_unlock_updates(self):
        flow = self.flow_id_from_path(self.new_flow())
        ticket_id = Path(self.new_ticket("Stable close metadata")).name
        self.cmd(
            "flow-link",
            "--project",
            str(self.project),
            "--flow",
            flow,
            "--ticket",
            ticket_id,
            "--milestone",
            "M1",
        )
        self.complete_ticket_artifacts(ticket_id, freeze=False)
        self.cmd(
            "review-freeze",
            "--project",
            str(self.project),
            "--ticket",
            ticket_id,
            "--allow-empty",
        )
        config = ticket_tool.load_config(self.project)
        ticket = self.ticket_path(ticket_id)
        frozen = ticket_tool.change_fingerprint(self.project, config, ticket)

        self.cmd("close", "--project", str(self.project), "--ticket", ticket_id)
        self.assertEqual(frozen, ticket_tool.change_fingerprint(self.project, config, ticket))

        dependent = Path(self.new_ticket("Dependent")).name
        self.cmd(
            "flow-link",
            "--project",
            str(self.project),
            "--flow",
            flow,
            "--ticket",
            dependent,
            "--milestone",
            "M1",
            "--depends-on",
            ticket_id,
        )
        self.assertEqual(frozen, ticket_tool.change_fingerprint(self.project, config, ticket))

    def test_review_metadata_normalization_preserves_legacy_markers(self):
        ticket_id = Path(self.new_ticket("Marker compatibility")).name
        readme = self.ticket_path(ticket_id) / "README.md"
        for label, value in {
            "Unlocks": "TD999999",
            "Review status": "REVIEW STALE",
            "Reviewed change fingerprint": "abc",
            "Status": "DONE",
            "Done": "2026-08-03",
            "Completed at": "2026-08-03",
        }.items():
            ticket_tool.write_metadata_field(readme, label, value)
        normalized = ticket_tool.normalized_file_text(readme)
        for label, marker in ticket_tool.TICKET_METADATA_MARKERS.items():
            self.assertIn(f"**{label}:** {marker}", normalized)

    def test_console_safe_text_escapes_unencodable_status(self):
        value = "milestone: triển khai"
        self.assertEqual(value, ticket_tool.console_safe_text(value, "utf-8"))
        self.assertIn(r"\u1ec3", ticket_tool.console_safe_text(value, "cp1252"))

if __name__ == "__main__":
    unittest.main()
