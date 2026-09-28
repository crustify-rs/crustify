from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from crustify import translate


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
             fields: list[str] | None = None,
             home: str = "crustify/rust/demo/src/lib.rs") -> dict:
        return {"name": name, "defined_in": defined_in, "kind": kind,
                "field_anchors": fields or [], "home": home}

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
                "home": "crustify/rust/demo/src/lib.rs",
            }],
        }))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(self.repo), *args], check=check,
            capture_output=True, text=True,
        )

    def _worktree(self, name: str) -> Path:
        """Fork a batch worktree the way the orchestrator now does."""
        path = self.repo / "crustify/.worktrees" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        self.git("worktree", "add", "--quiet", "-b",
                 f"crustify/batches/{name}", str(path), "refs/heads/wave-0")
        return path

    def test_the_harness_creates_no_branch_or_worktree(self) -> None:
        """The orchestrator owns both; the harness runs in the tree it is given."""
        before_refs = self.git("for-each-ref", "--format=%(refname)", "refs/heads").stdout
        before_trees = self.git("worktree", "list", "--porcelain").stdout
        tree = self._worktree("batch-a")
        calls: list[Path] = []

        class FakeAgent:
            def __init__(self, workdir, **kwargs):
                calls.append(workdir)

            def run(self):
                pass

        with (mock.patch("crustify.layout._REPO_ROOT", self.repo),
              mock.patch("crustify.agents.translate.TranslateAgent", FakeAgent)):
            translate.execute(tree, self.batch, base_branch="wave-0",
                              output=self.output)
        self.assertEqual(calls, [tree])
        # Only the worktree the test forked itself is new.
        self.assertEqual(
            set(self.git("for-each-ref", "--format=%(refname)",
                         "refs/heads").stdout.split())
            - set(before_refs.split()),
            {"refs/heads/crustify/batches/batch-a"})
        self.assertEqual(
            self.git("worktree", "list", "--porcelain").stdout.count("worktree "),
            before_trees.count("worktree ") + 1)

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
            git_base="wave-0",
            artifact_dir=self.output,
            log_stem="batch-id",
        )
        arguments = agent._arguments()
        # The body rides the system slot, so the worklist and the wave branch
        # are rendered there rather than into the user turn.
        rendered = agent._body().format(**arguments)
        self.assertEqual(arguments["git_base"], "wave-0")
        self.assertEqual(json.loads(arguments["worklist"])["route"], "type")
        self.assertIn("unchecked-out wave integration branch: `wave-0`", rendered)
        self.assertNotIn("{", agent._prompt())

    def test_artifacts_take_fixed_names_in_the_batch_directory(self) -> None:
        """`--output` is the batch's own directory, so nothing has to be
        unique; the orchestrator names a batch by choosing where it writes."""
        tree = self._worktree("batch-b")
        calls: list[dict] = []

        class FakeAgent:
            def __init__(self, workdir, **kwargs):
                calls.append({"workdir": workdir, **kwargs})

            def run(self):
                call = calls[-1]
                from crustify.agentlog import open_agent_log
                with open_agent_log(
                        call["artifact_dir"], call["log_stem"],
                        stage="wrap-type_Frame") as log:
                    log.line("fake translator")
                    log.usage({"provider": "test", "model": "test", "requests": []})

        with (mock.patch("crustify.layout._REPO_ROOT", self.repo),
              mock.patch("crustify.agents.translate.TranslateAgent", FakeAgent)):
            translate.execute(
                tree, self.batch, base_branch="wave-0", output=self.output)

        self.assertEqual(len(calls), 1)
        call = calls[0]
        self.assertEqual(call["git_base"], "wave-0")
        self.assertEqual(call["log_stem"], "translator")
        self.assertTrue((self.output / "translator.log").is_file())
        self.assertTrue((self.output / "translator.usage.json").is_file())
        usage = json.loads((self.output / "translator.usage.json").read_text())
        self.assertEqual(usage["stage"], "wrap-type_Frame")
        # The worktree is the agent's, forked from the wave branch, and the
        # authored home the batch names is present in it.
        home = call["workdir"] / "crustify/rust/demo/src/lib.rs"
        self.assertTrue(home.is_file())
        self.assertNotIn("crustify:todo", home.read_text())

    def test_agent_failure_leaves_the_worktree_alone(self) -> None:
        """The harness neither creates nor purges the tree, so a failed batch
        keeps its worktree for inspection without the harness doing anything."""
        tree = self._worktree("batch-c")

        class FailingAgent:
            def __init__(self, workdir, **kwargs):
                pass

            def run(self):
                raise RuntimeError("agent failed")

        with (mock.patch("crustify.layout._REPO_ROOT", self.repo),
              mock.patch("crustify.agents.translate.TranslateAgent", FailingAgent),
              self.assertRaisesRegex(RuntimeError, "agent failed")):
            translate.execute(tree, self.batch, base_branch="wave-0",
                              output=self.output)
        self.assertTrue(tree.is_dir())

    def test_concurrent_sibling_landings_reject_loser_then_rebase(self) -> None:
        first, second = self._worktree("first"), self._worktree("second")
        for tree, filename in ((first, "first.txt"), (second, "second.txt")):
            (tree / filename).write_text(filename + "\n")
            subprocess.run(["git", "-C", str(tree), "add", filename], check=True)
            subprocess.run(
                ["git", "-C", str(tree), "commit", "-qm", filename], check=True)

        common = self.git("rev-parse", "--git-common-dir").stdout.strip()
        commands = [
            ["git", "-C", str(tree), "push", "-q", common,
             "HEAD:refs/heads/wave-0"]
            for tree in (first, second)
        ]
        attempts = [
            subprocess.Popen(command, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True)
            for command in commands
        ]
        results = [attempt.communicate() + (attempt.returncode,)
                   for attempt in attempts]
        self.assertEqual(sorted(result[2] for result in results).count(0), 1)
        winner_index = next(i for i, result in enumerate(results) if result[2] == 0)
        loser_index = 1 - winner_index
        winner = (first, second)[winner_index]
        loser = (first, second)[loser_index]
        self.assertEqual(
            self.git("rev-parse", "wave-0").stdout.strip(),
            self.git("-C", str(winner), "rev-parse", "HEAD").stdout.strip(),
        )
        subprocess.run(
            ["git", "-C", str(loser), "rebase", "wave-0"], check=True,
            capture_output=True, text=True)
        subprocess.run(
            ["git", "-C", str(loser), "push", "-q", common,
             "HEAD:refs/heads/wave-0"], check=True)

        self.git("worktree", "remove", "--force", str(first))
        self.git("worktree", "remove", "--force", str(second))
        tree_files = self.git("ls-tree", "--name-only", "wave-0").stdout.splitlines()
        self.assertIn("first.txt", tree_files)
        self.assertIn("second.txt", tree_files)
        self.assertFalse(first.exists())
        self.assertFalse(second.exists())


if __name__ == "__main__":
    unittest.main()
