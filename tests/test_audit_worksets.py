from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from crustify_audit.agents.base import AuditAgent
from crustify_audit.layout import Layout
from crustify_audit import unsafe_scan


class DeterministicWorkspaceTests(unittest.TestCase):
    def test_campaign_repo_resolves_crustify_rust_but_keeps_artifacts_at_root(self) -> None:
        with TemporaryDirectory() as temporary:
            repo = Path(temporary)
            workspace = repo / "crustify" / "rust"
            workspace.mkdir(parents=True)
            (workspace / "Cargo.toml").write_text("[workspace]\n")
            layout = Layout(repo)

            self.assertEqual(layout.workspace, workspace)
            self.assertEqual(layout.scan, repo / "crustify/audit/unsafe.json")

            with mock.patch(
                    "crustify_audit.unsafe_scan.driver.measure",
                    return_value=({"code_lines": 1}, [])) as measure:
                document = unsafe_scan.compose(layout)

            measure.assert_called_once_with(workspace, names=None)
            self.assertEqual(document["crate_path"], str(workspace))

    def test_root_cargo_workspace_wins_over_campaign_fallback(self) -> None:
        with TemporaryDirectory() as temporary:
            repo = Path(temporary)
            (repo / "Cargo.toml").write_text("[workspace]\n")
            campaign = repo / "crustify" / "rust"
            campaign.mkdir(parents=True)
            (campaign / "Cargo.toml").write_text("[workspace]\n")

            self.assertEqual(Layout(repo).workspace, repo)


class AuditWorksetTests(unittest.TestCase):
    def agent(self, objective: str, workset: list[str] | None) -> AuditAgent:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        return AuditAgent(
            Layout(Path(temporary.name)),
            objective=objective,
            workset=workset,
            instruments=["miri"],
        )

    def test_patch_workset_names_advisories(self) -> None:
        advisory = "crustify/audit/advisories/untethered-reference-owners"
        prompt = self.agent("patch", [advisory])._workset_text()

        self.assertIn("These advisories, and only these", prompt)
        self.assertIn(advisory, prompt)
        self.assertNotIn("These files", prompt)

    def test_patch_without_workset_repairs_every_advisory(self) -> None:
        prompt = self.agent("patch", None)._workset_text()

        self.assertIn("Every confirmed advisory", prompt)
        self.assertIn("do not hunt for new findings", prompt)

    def test_revisit_workset_still_names_leads(self) -> None:
        lead = "crustify/audit/leads/open-question.md"
        prompt = self.agent("revisit", [lead])._workset_text()

        self.assertIn("These leads, and only these", prompt)
        self.assertIn(lead, prompt)

    def test_audit_workset_still_names_source_files(self) -> None:
        source = "src/wrapper.rs"
        prompt = self.agent("audit", [source])._workset_text()

        self.assertIn("These files, and only these", prompt)
        self.assertIn(source, prompt)


if __name__ == "__main__":
    unittest.main()
