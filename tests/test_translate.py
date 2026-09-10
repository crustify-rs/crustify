from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from crustify import translate, worktree


class BatchValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "batch.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def load(self, doc: object) -> translate.Batch:
        self.path.write_text(json.dumps(doc))
        return translate.load_batch(self.path)

    @staticmethod
    def item(name: str = "thing", *, kind: str = "symbol",
             defined_in: str | None = "include/thing.h",
             fields: list[str] | None = None) -> dict:
        return {"name": name, "defined_in": defined_in, "kind": kind,
                "field_anchors": fields or []}

    def test_thin_symbol_and_callback_batch(self) -> None:
        batch = self.load({
            "objective": "wrap",
            "items": [self.item(), self.item("visit", kind="callback")],
        })
        self.assertEqual(batch.route, "symbol")
        self.assertEqual(batch.objective, "wrap")

    def test_type_field_anchors_are_preserved(self) -> None:
        batch = self.load({
            "objective": "port",
            "items": [self.item("Frame", kind="type", fields=["data", "size"])],
        })
        self.assertEqual(batch.items[0]["field_anchors"], ["data", "size"])

    def test_rejects_mixed_routes(self) -> None:
        with self.assertRaisesRegex(SystemExit, "mixed agent routes"):
            self.load({
                "objective": "wrap",
                "items": [self.item(), self.item("Frame", kind="type")],
            })

    def test_rejects_unknown_fields_and_duplicate_items(self) -> None:
        item = self.item()
        with self.assertRaisesRegex(SystemExit, "unknown batch field"):
            self.load({"objective": "wrap", "items": [item], "route": "symbol"})
        with self.assertRaisesRegex(SystemExit, "duplicate item"):
            self.load({"objective": "wrap", "items": [item, item]})

    def test_rejects_invalid_or_misrouted_field_anchors(self) -> None:
        with self.assertRaisesRegex(SystemExit, "C field identifiers"):
            self.load({
                "objective": "wrap",
                "items": [self.item("Frame", kind="type", fields=["bad.field"])],
            })
        with self.assertRaisesRegex(SystemExit, "must be empty"):
            self.load({
                "objective": "wrap",
                "items": [self.item(fields=["field"])],
            })

    def test_raw_lifetime_is_exactly_one_known_tier(self) -> None:
        batch = self.load({
            "objective": "port",
            "items": [self.item("void", kind="raw-lifetime", defined_in=None)],
        })
        self.assertEqual(batch.route, "raw-lifetime")
        self.assertEqual(translate._task_objective(batch), "wrap")

        with self.assertRaisesRegex(SystemExit, "exactly one void or string"):
            self.load({
                "objective": "wrap",
                "items": [self.item("other", kind="raw-lifetime", defined_in=None)],
            })
        with self.assertRaisesRegex(SystemExit, "must be null"):
            self.load({
                "objective": "wrap",
                "items": [self.item("void", kind="raw-lifetime")],
            })


class GitHarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.repo / "crustify/rust/demo/src").mkdir(parents=True)
        (self.repo / "crustify/rust/demo/src/lib.rs").write_text("pub struct Frame;\n")
        crates = {
            "crates": {
                "demo": {
                    "crate_path": "crustify/rust/demo",
                    "depends_on": [],
                    "modules": {
                        "root": {
                            "rs": {
                                "src/lib.rs": {
                                    "tu": None,
                                    "headers": ["include/frame.h"],
                                    "members": {
                                        "functions": [],
                                        "types": ["Frame"],
                                        "callbacks": [],
                                        "macros": [],
                                        "globals": [],
                                    },
                                }
                            }
                        }
                    },
                }
            }
        }
        (self.repo / "crustify/crates.json").write_text(json.dumps(crates))
        (self.repo / "README").write_text("test\n")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.git("branch", "wave-0")
        self.output = Path(self.tmp.name) / "logs"
        self.output.mkdir()
        self.batch = Path(self.tmp.name) / "batch.json"
        self.batch.write_text(json.dumps({
            "objective": "wrap",
            "items": [{
                "name": "Frame",
                "defined_in": "include/frame.h",
                "kind": "type",
                "field_anchors": ["data"],
            }],
        }))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(self.repo), *args], check=check,
            capture_output=True, text=True,
        )

    def test_base_branch_must_exist_and_be_unchecked_out(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "does not exist"):
            worktree.validate_base_branch(self.repo, "missing")
        current = self.git("branch", "--show-current").stdout.strip()
        with self.assertRaisesRegex(RuntimeError, "is checked out"):
            worktree.validate_base_branch(self.repo, current)

    def test_worktree_is_created_from_base_branch(self) -> None:
        tree = worktree.add_batch_worktree(self.repo, "wave-0", "batch-a")
        self.assertEqual(tree.base_commit, self.git("rev-parse", "wave-0").stdout.strip())
        self.assertEqual(
            subprocess.run(
                ["git", "-C", str(tree.path), "branch", "--show-current"],
                check=True, capture_output=True, text=True,
            ).stdout.strip(),
            "crustify/batch/batch-a",
        )
        self.assertEqual((tree.path / "README").read_text(), "test\n")

    def test_dry_run_does_not_create_refs_or_worktrees(self) -> None:
        before_refs = self.git("for-each-ref", "--format=%(refname)", "refs/heads").stdout
        before_trees = self.git("worktree", "list", "--porcelain").stdout
        with mock.patch("crustify.layout._REPO_ROOT", self.repo):
            translate.execute(
                self.repo, self.batch, base_branch="wave-0",
                output=self.output, dry_run=True,
            )
        self.assertEqual(
            self.git("for-each-ref", "--format=%(refname)", "refs/heads").stdout,
            before_refs,
        )
        self.assertEqual(self.git("worktree", "list", "--porcelain").stdout,
                         before_trees)

    def test_output_directory_must_already_exist(self) -> None:
        missing = Path(self.tmp.name) / "missing-logs"
        with (mock.patch("crustify.layout._REPO_ROOT", self.repo),
              self.assertRaisesRegex(SystemExit, "existing directory")):
            translate.execute(
                self.repo, self.batch, base_branch="wave-0",
                output=missing, dry_run=True,
            )
        self.assertFalse(missing.exists())

    def test_translate_agent_renders_thin_worklist_and_base_branch(self) -> None:
        from crustify.agents.translate import TranslateAgent

        items = json.loads(self.batch.read_text())["items"]
        agent = TranslateAgent(
            self.repo,
            route="type",
            items=items,
            objective="review",
            campaign_objective="review",
            prompt_capabilities=(),
            repo_root=self.repo,
            git_base="wave-0",
            log_dir=self.output,
            log_stem="batch-id",
        )
        arguments = agent._arguments()
        rendered = agent._prompt().format(**arguments)
        self.assertEqual(arguments["git_base"], "wave-0")
        self.assertEqual(json.loads(arguments["worklist"])["route"], "type")
        self.assertIn("unchecked-out wave integration branch: `wave-0`", rendered)

    def test_harness_places_anchors_and_uses_explicit_log_names(self) -> None:
        calls: list[dict] = []

        class FakeAgent:
            @staticmethod
            def configured_capabilities(_layout):
                return ()

            def __init__(self, _target, **kwargs):
                calls.append(kwargs)

            def run(self):
                call = calls[-1]
                rs = call["repo_root"] / "crustify/rust/demo/src/lib.rs"
                self.assert_anchor = rs.read_text()
                from crustify.agentlog import open_agent_log
                with open_agent_log(
                        call["log_dir"], call["log_stem"],
                        stage="wrap-type_Frame") as log:
                    log.line("fake translator")
                    log.usage({"provider": "test", "model": "test", "requests": []})

        with (mock.patch("crustify.layout._REPO_ROOT", self.repo),
              mock.patch("crustify.agents.translate.TranslateAgent", FakeAgent)):
            translate.execute(
                self.repo, self.batch, base_branch="wave-0", output=self.output)

        self.assertEqual(len(calls), 1)
        call = calls[0]
        self.assertEqual(call["git_base"], "wave-0")
        self.assertRegex(call["log_stem"],
                         r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_[0-9a-f]{8}$")
        self.assertTrue((self.output / f"{call['log_stem']}.log").is_file())
        self.assertTrue((self.output / f"{call['log_stem']}.usage.json").is_file())
        usage = json.loads(
            (self.output / f"{call['log_stem']}.usage.json").read_text())
        self.assertEqual(usage["stage"], "wrap-type_Frame")
        anchored = (call["repo_root"] / "crustify/rust/demo/src/lib.rs").read_text()
        self.assertIn("// crustify:todo: Frame", anchored)
        self.assertIn("// crustify:todo: Frame.data", anchored)

    def test_agent_failure_retains_batch_worktree(self) -> None:
        class FailingAgent:
            @staticmethod
            def configured_capabilities(_layout):
                return ()

            def __init__(self, _target, **kwargs):
                self.repo_root = kwargs["repo_root"]

            def run(self):
                raise RuntimeError("agent failed")

        with (mock.patch("crustify.layout._REPO_ROOT", self.repo),
              mock.patch("crustify.agents.translate.TranslateAgent", FailingAgent),
              self.assertRaisesRegex(RuntimeError, "agent failed")):
            translate.execute(
                self.repo, self.batch, base_branch="wave-0", output=self.output)
        self.assertEqual(len(list((self.repo / "crustify/.worktrees").iterdir())), 1)

    def test_atomic_landing_recipe_rebases_loser_and_allows_pruning(self) -> None:
        first = worktree.add_batch_worktree(self.repo, "wave-0", "first")
        second = worktree.add_batch_worktree(self.repo, "wave-0", "second")
        for tree, filename in ((first, "first.txt"), (second, "second.txt")):
            (tree.path / filename).write_text(filename + "\n")
            subprocess.run(["git", "-C", str(tree.path), "add", filename], check=True)
            subprocess.run(
                ["git", "-C", str(tree.path), "commit", "-qm", filename], check=True)

        common = self.git("rev-parse", "--git-common-dir").stdout.strip()
        subprocess.run(
            ["git", "-C", str(first.path), "push", "-q", common,
             "HEAD:refs/heads/wave-0"], check=True)
        rejected = subprocess.run(
            ["git", "-C", str(second.path), "push", "-q", common,
             "HEAD:refs/heads/wave-0"], capture_output=True, text=True)
        self.assertNotEqual(rejected.returncode, 0)
        subprocess.run(
            ["git", "-C", str(second.path), "rebase", "wave-0"], check=True,
            capture_output=True, text=True)
        subprocess.run(
            ["git", "-C", str(second.path), "push", "-q", common,
             "HEAD:refs/heads/wave-0"], check=True)

        self.git("worktree", "remove", "--force", str(first.path))
        self.git("worktree", "remove", "--force", str(second.path))
        tree_files = self.git("ls-tree", "--name-only", "wave-0").stdout.splitlines()
        self.assertIn("first.txt", tree_files)
        self.assertIn("second.txt", tree_files)
        self.assertFalse(first.path.exists())
        self.assertFalse(second.path.exists())


if __name__ == "__main__":
    unittest.main()
