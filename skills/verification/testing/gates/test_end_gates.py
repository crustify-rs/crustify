"""`end-gates`: snapshots, skip checks, stages and the summary, over a tiny workspace."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# The script under test, beside this file: a module without a .py name.
_loader = importlib.machinery.SourceFileLoader(
    "end_gates", str(Path(__file__).with_name("end-gates")))
_spec = importlib.util.spec_from_loader("end_gates", _loader)
eg = importlib.util.module_from_spec(_spec)
sys.modules["end_gates"] = eg
_loader.exec_module(eg)

LIB = """
pub fn one() -> u32 { 1 }

#[cfg(test)]
mod tests {
    #[test]
    fn one() { assert_eq!(super::one(), 1); }
    #[test]
    fn one_more() { assert_eq!(super::one() + 1, 2); }
    #[test]
    fn fails_on_demand() { assert!(std::env::var_os("DEMO_FAIL").is_none()); }
}
"""

IT = """
#[test]
fn quick() { assert_eq!(demo::one(), 1); }
#[test]
fn slow() { std::thread::sleep(std::time::Duration::from_secs(60)); }
#[test]
fn sees_its_builds() {
    let here = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    assert!(here.join("builds/marker").exists());
}
"""

# A library and a test that format and lint clean, but for `two` under the feature `extra`.
LINT_LIB = """pub fn one() -> u32 {
    1
}

#[cfg(feature = "extra")]
pub fn two() -> u32 {
    return 2;
}
"""

LINT_IT = """#[test]
fn quick() {
    assert_eq!(demo::one(), 1);
}
"""

# A runner that takes the variant first, as a campaign's does, and runs plain cargo.
RUNNER = """#!/bin/sh
echo "variant $1" >&2
shift
exec cargo "$@"
"""


def sh(cwd: Path, *cmd: str) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


@unittest.skipUnless(shutil.which("cargo") and shutil.which("git"), "needs cargo and git")
class EndGates(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        t = self.tree = self.tmp / "tree"
        (t / "src").mkdir(parents=True)
        (t / "tests").mkdir()
        (t / "Cargo.toml").write_text(
            '[package]\nname = "demo"\nversion = "0.1.0"\nedition = "2021"\n\n'
            '[workspace]\n')
        (t / "src/lib.rs").write_text(LIB)
        (t / "tests/it.rs").write_text(IT)
        (t / ".gitignore").write_text("/target\n/builds\n/crustify/tmp\n")
        (t / "builds").mkdir()
        (t / "builds/marker").write_text("")
        self.runner = self.tmp / "runner.sh"
        self.runner.write_text(RUNNER)
        self.runner.chmod(0o755)
        sh(t, "git", "init", "-q")
        sh(t, "git", "add", "-A")
        sh(t, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
        self.logs = self.tmp / "logs"
        os.environ.setdefault("CARGO_HOME", "/root/.cargo")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def gates(self, *args: str, skips: str | None = None) -> int:
        argv = [str(self.tree), "--logs", str(self.logs), "--runner", str(self.runner),
                "--link", "builds", *args]
        if skips is not None:
            f = self.tmp / "skips"
            f.write_text(skips)
            argv += ["--skip-file", str(f)]
        return eg.main(argv)

    def summary(self) -> dict[str, dict]:
        return {r["run"]: r for r in
                json.loads((self.logs / "summary.json").read_text())}

    def test_snapshot_is_the_commit_with_links_and_a_repository(self) -> None:
        (self.tree / "src/lib.rs").write_text("uncommitted")
        (self.tree / "untracked.txt").write_text("")
        snap = self.tmp / "snap"
        eg.snapshot(self.tree, snap, "HEAD", ["builds"])
        self.assertEqual((snap / "src/lib.rs").read_text(), LIB)
        self.assertFalse((snap / "untracked.txt").exists())
        self.assertTrue((snap / "builds").is_symlink())
        self.assertTrue((snap / "builds/marker").exists())
        self.assertTrue((snap / ".git").is_dir())

    def test_working_tree_snapshot_takes_uncommitted_and_untracked_files(self) -> None:
        (self.tree / "src/lib.rs").write_text("uncommitted")
        (self.tree / "untracked.txt").write_text("")
        snap = self.tmp / "snap"
        eg.snapshot(self.tree, snap, None, [])
        self.assertEqual((snap / "src/lib.rs").read_text(), "uncommitted")
        self.assertTrue((snap / "untracked.txt").exists())
        self.assertFalse((snap / "target").exists())

    def test_a_tracked_path_is_not_linked(self) -> None:
        with self.assertRaises(eg.Refused):
            eg.snapshot(self.tree, self.tmp / "snap", "HEAD", ["src"])

    def test_a_skip_that_names_no_test_fails_before_any_stage(self) -> None:
        rc = self.gates("--stages", "plain", skips="plain lib tests::none\n")
        self.assertEqual(rc, 2)
        self.assertFalse((self.logs / "plain.log").exists())

    def test_a_skip_whose_name_begins_another_tests_skips_it_alone(self) -> None:
        rc = self.gates("--stages", "plain,bsan", "--stage-env", "bsan:RUST_TEST_THREADS=1",
                        skips="plain lib tests::one\nplain it slow\n"
                              "bsan lib tests::one\nbsan it slow\n")
        self.assertEqual(rc, 0)
        s = self.summary()
        for run in ("plain", "bsan-lib"):
            self.assertIn("--exact", s[run]["command"], run)
            self.assertIn("--skip tests::one", s[run]["command"], run)
            log = Path(s[run]["log"]).read_text()
            self.assertIn("tests::one_more ... ok", log, run)
            self.assertNotIn("tests::one ... ok", log, run)

    def test_a_variant_skip_two_binaries_hold_fails(self) -> None:
        (self.tree / "tests/other.rs").write_text("#[test]\nfn quick() {}\n")
        sh(self.tree, "git", "add", "-A")
        sh(self.tree, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "o")
        rc = self.gates("--stages", "plain", skips="plain it quick\n")
        self.assertEqual(rc, 2)
        self.assertFalse((self.logs / "plain.log").exists())
        self.assertEqual(self.gates("--stages", "bsan", skips="bsan it quick\nbsan it slow\n"), 0)

    def test_a_skip_of_an_unknown_binary_fails(self) -> None:
        rc = self.gates("--stages", "plain", skips="plain nope tests::one_more\n")
        self.assertEqual(rc, 2)

    def test_stages_run_in_order_with_their_skips_and_env(self) -> None:
        rc = self.gates("--stages", "plain,bsan", "--stage-env", "plain:DEMO_FAIL=1",
                        skips="# hangs\nplain it slow\nbsan it slow\n")
        self.assertEqual(rc, 1)
        s = self.summary()
        self.assertEqual(list(s)[:2], ["plain", "bsan-build"])
        self.assertEqual(set(list(s)[2:]), {"bsan-lib", "bsan-it"})
        self.assertNotEqual(s["plain"]["exit"], 0)
        self.assertEqual(s["plain"]["failed"], ["tests::fails_on_demand"])
        self.assertIn("--exact --skip slow", s["plain"]["command"])
        for run in ("bsan-build", "bsan-lib", "bsan-it"):
            self.assertEqual(s[run]["exit"], 0, run)
        self.assertIn("--skip slow", s["bsan-it"]["command"])
        self.assertNotIn("--skip", s["bsan-lib"]["command"])
        self.assertIn("variant bsan", Path(s["bsan-it"]["log"]).read_text())
        self.assertTrue(any("3 passed" in l or "2 passed" in l
                            for l in s["bsan-it"]["results"]))
        self.assertIn("plain: exit", (self.logs / "summary.txt").read_text())

    def test_a_binary_past_its_timeout_is_reported_and_fails(self) -> None:
        rc = self.gates("--stages", "bsan", "--timeout", "20")
        self.assertEqual(rc, 1)
        s = self.summary()
        self.assertTrue(s["bsan-it"]["timed_out"])
        self.assertFalse(s["bsan-lib"]["timed_out"])
        self.assertEqual(s["bsan-lib"]["exit"], 0)

    def test_lint_checks_the_commit_once_per_feature_set(self) -> None:
        # A tree that formats and lints clean with no feature, whose feature `extra` adds a
        # lint `-D warnings` refuses; the working tree's unformatted edit is not the commit's.
        cargo = self.tree / "Cargo.toml"
        cargo.write_text(cargo.read_text() + "\n[features]\nextra = []\n")
        (self.tree / "src/lib.rs").write_text(LINT_LIB)
        (self.tree / "tests/it.rs").write_text(LINT_IT)
        sh(self.tree, "git", "add", "-A")
        sh(self.tree, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "lint")
        (self.tree / "src/lib.rs").write_text(LINT_LIB + "pub fn   three() -> u32 { 3 }\n")
        rc = self.gates("--stages", "lint", "--lint-features", "extra", "--nightly", "stable")
        self.assertEqual(rc, 1)
        s = self.summary()
        self.assertEqual(list(s), ["lint-fmt", "lint-clippy", "lint-clippy-extra"])
        self.assertEqual(s["lint-fmt"]["exit"], 0)
        self.assertEqual(s["lint-clippy"]["exit"], 0)
        self.assertNotEqual(s["lint-clippy-extra"]["exit"], 0)
        self.assertIn("--features extra", s["lint-clippy-extra"]["command"])
        self.assertTrue(s["lint-clippy"]["command"].endswith("-- -D warnings"))
        self.assertIn("variant plain", Path(s["lint-clippy"]["log"]).read_text())
        self.assertIn("needless_return", Path(s["lint-clippy-extra"]["log"]).read_text())
        # Committed, the edit fails the format check.
        sh(self.tree, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "fmt")
        rc = self.gates("--stages", "lint", "--nightly", "stable")
        self.assertEqual(rc, 1)
        s = self.summary()
        self.assertNotEqual(s["lint-fmt"]["exit"], 0)
        self.assertEqual(s["lint-clippy"]["exit"], 0)


if __name__ == "__main__":
    unittest.main()
