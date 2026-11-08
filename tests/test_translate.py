from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from crustify import config, translate

#: The run settings every task carries.
RUN = {"backend": "claude", "billing": "subscription"}
#: Where every task's batch sits in the schedule.
PLACE = {"wave": 0, "batch": 0, "link_unit": "demo", "module": "src/core.c",
         "foundational": False}


def _reset_run() -> None:
    """A task applies its run settings process-wide; tests put them back."""
    config.BACKEND = "claude"
    config.BILLING = "subscription"
    config.MODEL_PROXY = None
    config.PROVIDER_ARGS = []


class BatchValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "task.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def load(self, doc: dict, *, complete: bool = True) -> translate.Batch:
        if complete:
            doc = {**RUN, **PLACE, "base_branch": "wave-0", **doc}
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
        self.assertEqual(batch.base_branch, "wave-0")
        self.assertEqual(batch.run, translate.RunSettings(**RUN))

    def test_batch_fields_place_the_task_in_the_schedule(self) -> None:
        doc = {"objective": "wrap", "items": [self.item()]}
        placement = self.load({**doc, "wave": 7, "batch": 2}).placement
        self.assertEqual(placement.batch_id, "wave-7/batch-2")
        self.assertEqual(placement.module_label, "demo/src/core.c")
        self.assertEqual(self.load({**doc, "foundational": True}).placement.module_label,
                         "demo/src/core.c (foundational)")
        self.assertEqual(
            self.load({**doc, "module": None}).placement.module_label, "none")
        for field in ("wave", "batch", "link_unit", "module", "foundational"):
            with self.subTest(missing=field), \
                    self.assertRaisesRegex(SystemExit, f"missing task field.*{field}"):
                full = {**RUN, **PLACE, "base_branch": "wave-0", **doc}
                del full[field]
                self.load(full, complete=False)
        for bad in ({"wave": -1}, {"batch": "0"}, {"wave": True}):
            with self.subTest(bad=bad), \
                    self.assertRaisesRegex(SystemExit, "non-negative index"):
                self.load({**doc, **bad})
        with self.assertRaisesRegex(SystemExit, "link_unit must be a name or null"):
            self.load({**doc, "link_unit": ""})
        for bad in ("", 3, True):
            with self.subTest(module=bad), \
                    self.assertRaisesRegex(SystemExit, "module must be a name or null"):
                self.load({**doc, "module": bad})
        with self.assertRaisesRegex(SystemExit, "true or false"):
            self.load({**doc, "foundational": "yes"})
        with self.assertRaisesRegex(SystemExit, "no module is not foundational"):
            self.load({**doc, "module": None, "foundational": True})
        with self.assertRaisesRegex(SystemExit, "needs its link_unit"):
            self.load({**doc, "link_unit": None})

    def test_run_settings_and_branch_are_required_and_checked(self) -> None:
        doc = {"objective": "wrap", "items": [self.item()]}
        for field in ("backend", "billing", "base_branch"):
            with self.subTest(missing=field), \
                    self.assertRaisesRegex(SystemExit, f"missing task field.*{field}"):
                full = {**RUN, **PLACE, "base_branch": "wave-0", **doc}
                del full[field]
                self.load(full, complete=False)
        with self.assertRaisesRegex(SystemExit, "unknown backend"):
            self.load({**doc, "backend": "gemini"})
        with self.assertRaisesRegex(SystemExit, "unknown billing"):
            self.load({**doc, "billing": "free"})
        with self.assertRaisesRegex(SystemExit, "args must be an array"):
            self.load({**doc, "args": "--model opus"})
        with self.assertRaisesRegex(SystemExit, "names its backend, not a model"):
            self.load({**doc, "model": "anthropic/claude-opus-5"})
        run = self.load({**doc, "model_proxy": "openrouter", "billing": "api",
                         "args": ["--model", "anthropic/claude-opus-5"]}).run
        self.assertEqual((run.model_proxy, run.args),
                         ("openrouter", ("--model", "anthropic/claude-opus-5")))
        with self.assertRaisesRegex(SystemExit, "base_branch must name a branch"):
            self.load({**doc, "base_branch": ""})
        self.assertEqual(
            self.load({**doc, "base_branch": "refs/heads/wave-1"}).base_branch, "wave-1")

    def test_an_earlier_task_names_a_model(self) -> None:
        doc = {**PLACE, "base_branch": "wave-0", "objective": "wrap",
               "items": [self.item()], "billing": "subscription",
               "model": "anthropic/claude-opus-5"}
        run = self.load(doc, complete=False).run
        self.assertEqual((run.backend, run.billing, run.args),
                         ("claude", "subscription", ("--model", "claude-opus-5")))

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
        with self.assertRaisesRegex(SystemExit, "unknown task field"):
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

    def test_an_item_is_its_translation_unless_a_step_says_otherwise(self) -> None:
        batch = self.load({"objective": "port", "items": [self.item()]})
        self.assertEqual(batch.items[0]["step"], "translate")
        self.assertIsNone(batch.items[0]["of"])

    def test_deferred_steps_of_a_port_batch(self) -> None:
        frame = {"name": "Frame", "defined_in": "include/frame.h"}
        batch = self.load({"objective": "port", "items": [
            {**self.item("Frame", kind="type"), "step": "layout"},
            {**self.item("Packet", kind="type"), "step": "correct", "of": frame},
        ]})
        self.assertEqual([i["step"] for i in batch.items], ["layout", "correct"])
        self.assertEqual(batch.items[1]["of"], frame)
        # A consumer corrected after two steps of different types is two items.
        other = {"name": "Stream", "defined_in": "include/stream.h"}
        batch = self.load({"objective": "port", "items": [
            {**self.item(), "step": "correct", "of": frame},
            {**self.item(), "step": "correct", "of": other},
        ]})
        self.assertEqual(len(batch.items), 2)

    def test_rejects_invalid_deferred_steps(self) -> None:
        with self.assertRaisesRegex(SystemExit, "step must be one of"):
            self.load({"objective": "port", "items": [{**self.item(), "step": "nativize"}]})
        with self.assertRaisesRegex(SystemExit, "of must name"):
            self.load({"objective": "port", "items": [{**self.item(), "step": "std"}]})
        with self.assertRaisesRegex(SystemExit, "only carried by a correct or std"):
            self.load({"objective": "port", "items": [
                {**self.item(), "step": "retire",
                 "of": {"name": "x", "defined_in": "x.h"}}]})
        with self.assertRaisesRegex(SystemExit, "only carried by a port batch"):
            self.load({"objective": "wrap", "items": [
                {**self.item("Frame", kind="type"), "step": "layout"}]})

    def test_raw_lifetime_is_no_kind(self) -> None:
        # The foundational modules schedule ordinary
        # symbols and types: no marker item stands for them.
        with self.assertRaisesRegex(SystemExit, "kind must be one of"):
            self.load({
                "objective": "wrap",
                "items": [self.item("void", kind="raw-lifetime", defined_in=None)],
            })
        with self.assertRaisesRegex(SystemExit, "defined_in must be"):
            self.load({
                "objective": "wrap",
                "items": [self.item("av_free", kind="symbol", defined_in=None)],
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
        self.batch = self.output / "task.json"
        self.batch.write_text(json.dumps({
            **RUN,
            **PLACE,
            "base_branch": "wave-0",
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
        _reset_run()
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

        with mock.patch("crustify.agents.bind.BindAgent", FakeAgent):
            translate.execute(tree, self.batch, role="binder")
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
        translate.execute(self.repo, self.batch, role="binder", dry_run=True)
        self.assertEqual(
            self.git("for-each-ref", "--format=%(refname)", "refs/heads").stdout,
            before_refs,
        )
        self.assertEqual(self.git("worktree", "list", "--porcelain").stdout,
                         before_trees)

    def test_each_role_refuses_the_other_objective(self) -> None:
        with self.assertRaisesRegex(SystemExit, "spawn-binder"):
            translate.execute(self.repo, self.batch, role="translator", dry_run=True)
        port = Path(self.tmp.name) / "port.json"
        doc = json.loads(self.batch.read_text())
        port.write_text(json.dumps(dict(doc, objective="port")))
        with self.assertRaisesRegex(SystemExit, "spawn-translator"):
            translate.execute(self.repo, port, role="binder", dry_run=True)

    def test_the_task_file_must_exist(self) -> None:
        with self.assertRaisesRegex(SystemExit, "no task file at"):
            translate.execute(self.repo, self.output / "missing.json",
                              role="binder", dry_run=True)

    def test_bind_agent_renders_thin_worklist_and_base_branch(self) -> None:
        from crustify.agents.bind import BindAgent

        items = json.loads(self.batch.read_text())["items"]
        agent = BindAgent(
            self.repo,
            route="type",
            items=items,
            git_base="wave-0",
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
        """The run's session id goes into its task as soon as the CLI has one,
        and its session record into the session's directory in crustify's
        home. The agent runs under the task's backend and billing."""
        tree = self._worktree("batch-b")
        calls: list[dict] = []
        home = Path(self.tmp.name) / "home"

        class FakeAgent:
            on_session = None

            def __init__(self, workdir, **kwargs):
                calls.append({"workdir": workdir, **kwargs})

            def run(self):
                call = calls[-1]
                self.on_session("s-1")
                from crustify.agentlog import open_agent_log
                with open_agent_log(None, call["log_stem"], agent="binder") as log:
                    log.line("fake binder")
                    log.session({"backend": "claude", "session_id": "s-1",
                                 "exit_code": 0})

        with mock.patch("crustify.agents.bind.BindAgent", FakeAgent), \
                mock.patch.dict("os.environ", {"CRUSTIFY_HOME": str(home)}):
            translate.execute(tree, self.batch, role="binder")

        self.assertEqual(len(calls), 1)
        call = calls[0]
        self.assertEqual(call["git_base"], "wave-0")
        self.assertEqual(call["log_stem"], "binder")
        self.assertEqual(config.BACKEND, RUN["backend"])
        self.assertEqual(config.BILLING, RUN["billing"])
        self.assertEqual(json.loads(self.batch.read_text())["session_id"], "s-1")
        session = json.loads(
            (home / "sessions" / "s-1" / "binder.session.json").read_text())
        self.assertEqual((session["agent"], session["session_id"]),
                         ("binder", "s-1"))
        # The harness keeps no log and prices nothing in the run dir: the
        # transcript is the log, and `crustify usage` prices it.
        self.assertEqual(sorted(p.name for p in self.batch.parent.iterdir()),
                         [self.batch.name])
        # The run dir records one attempt: its task does not run again.
        with self.assertRaisesRegex(SystemExit, "already ran, as session s-1"):
            translate.execute(tree, self.batch, role="binder", dry_run=True)
        # The worktree is the agent's, forked from the wave branch, and the
        # authored home the batch names is present in it.
        home = call["workdir"] / "crustify/rust/demo/src/lib.rs"
        self.assertTrue(home.is_file())

    def test_agent_failure_leaves_the_worktree_alone(self) -> None:
        """The harness neither creates nor purges the tree, so a failed batch
        keeps its worktree for inspection without the harness doing anything."""
        tree = self._worktree("batch-c")

        class FailingAgent:
            def __init__(self, workdir, **kwargs):
                pass

            def run(self):
                raise RuntimeError("agent failed")

        with (mock.patch("crustify.agents.bind.BindAgent", FailingAgent),
              self.assertRaisesRegex(RuntimeError, "agent failed")):
            translate.execute(tree, self.batch, role="binder")
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
