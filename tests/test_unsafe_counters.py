import json
from pathlib import Path
import re
import unittest

from crustify_audit import driver, unsafe_scan

MAIN_RS = Path(driver.__file__).parent / "unsafe_driver" / "src" / "main.rs"


def _emission() -> tuple[list[str], list[str]]:
    """The driver's per-crate JSON line: its keys, and the value arguments, in order."""
    src = MAIN_RS.read_text()
    fmt = re.search(r'"\{\{\\"crate\\":\\"\{\}\\",(.*?)\\"sites\\":\{\}\}\}"', src).group(1)
    keys = re.findall(r'\\"(\w+)\\":\{\}', fmt)
    args = src[src.index(fmt):].split("\n", 2)[1]
    values = re.findall(r"\bc\.(\w+)", args)
    return keys, values


def _counts_fields() -> list[str]:
    src = MAIN_RS.read_text()
    body = re.search(r"struct Counts \{(.*?)\n\}", src, re.S).group(1)
    return re.findall(r"^\s*(\w+): u64", body, re.M)


class EmissionTests(unittest.TestCase):
    def test_emitted_keys_match_their_values_in_order(self) -> None:
        keys, values = _emission()
        self.assertEqual(keys, values)

    def test_every_count_is_emitted_and_merged(self) -> None:
        keys, _ = _emission()
        self.assertEqual(set(_counts_fields()), set(keys))
        self.assertEqual(set(driver._COUNTS), set(keys))

    def test_visibility_splits_are_emitted(self) -> None:
        keys, _ = _emission()
        for k in ("unsafe_fns_pub", "unsafe_fns_priv", "safe_fns_pub", "safe_fns_priv",
                  "raw_ptr_fn_pub_safe", "raw_ptr_ty_pub_fields_pub"):
            self.assertIn(k, keys)
            self.assertIn(k, driver.SITE_COUNTERS)

    def test_new_counts_sum_across_crates(self) -> None:
        line = lambda crate, n: json.dumps(
            {"crate": crate, "unsafe_blocks": 0, "safe_fns_pub": n, "raw_ptr_fn_pub_safe": n, "sites": {}})
        counts, _, seen, _ = driver._collect_emissions(
            "\n".join([line("a", 2), line("b", 3), line("c_sys", 100)]))
        self.assertEqual(seen, 2)
        self.assertEqual(counts["safe_fns_pub"], 5)
        self.assertEqual(counts["raw_ptr_fn_pub_safe"], 5)


class FfiboxTests(unittest.TestCase):
    def test_counters_match_the_driver_in_order(self) -> None:
        src = MAIN_RS.read_text()
        body = re.search(r"const FFIBOX_COUNTERS: &\[&str\] = &\[(.*?)\];", src, re.S).group(1)
        self.assertEqual(tuple(re.findall(r'"(\w+)"', body)), driver.FFIBOX_COUNTERS)

    def test_breakdowns_merge_across_crates_and_skip_sys(self) -> None:
        line = lambda crate, n: json.dumps({
            "crate": crate,
            "ffibox": {"fn_sig_ffibox_owner_pub": {"CBox": n}, "drop_impl": {"crate::Owner": 1}},
            "sites": {"fn_sig_ffibox_owner_pub": [{"file": "a.rs", "count": n, "lines": [1]}]}})
        _, sites, seen, ffibox = driver._collect_emissions(
            "\n".join([line("a", 2), line("b", 3), line("c_sys", 100)]))
        # an ffibox line is not a metrics line
        self.assertEqual(seen, 0)
        self.assertEqual(ffibox["fn_sig_ffibox_owner_pub"], {"CBox": 5})
        self.assertEqual(ffibox["drop_impl"], {"crate::Owner": 2})
        self.assertEqual(ffibox["fn_sig_ffibox_handle_priv"], {})
        self.assertEqual(sum(r["count"] for r in sites["fn_sig_ffibox_owner_pub"]), 5)

    def test_record_totals_every_counter(self) -> None:
        rec = unsafe_scan._ffibox_record({"fn_sig_ffibox_handle_pub": {"Ref": 4, "Mut": 1}})
        self.assertEqual(set(rec["counts"]), set(driver.FFIBOX_COUNTERS))
        self.assertEqual(rec["counts"]["fn_sig_ffibox_handle_pub"], 5)
        self.assertEqual(rec["counts"]["fn_sig_ffibox_owner_pub"], 0)
        self.assertIsNone(unsafe_scan._ffibox_record(None))

    def test_ffibox_sites_need_the_flag(self) -> None:
        with self.assertRaises(SystemExit) as e:
            unsafe_scan.site_counters(["fn_sig_ffibox_owner_pub"])
        self.assertIn("--ffibox", str(e.exception))
        self.assertEqual(unsafe_scan.site_counters(["fn_sig_ffibox_owner_pub"], ffibox=True),
                         ["fn_sig_ffibox_owner_pub"])
        self.assertNotIn("fn_sig_ffibox_owner_pub", unsafe_scan.site_counters(["all"]))
        self.assertIn("fn_sig_ffibox_owner_pub", unsafe_scan.site_counters(["all"], ffibox=True))


class SysCrateTests(unittest.TestCase):
    def test_emissions_of_sys_crates_are_skipped_by_name_or_links(self) -> None:
        line = lambda crate: json.dumps({"crate": crate, "unsafe_blocks": 1, "sites": {}})
        counts, _, seen, _ = driver._collect_emissions(
            "\n".join([line("safe"), line("ffmpeg_sys_the_third"), line("x_sys")]),
            {"ffmpeg_sys_the_third"})
        self.assertEqual(seen, 1)
        self.assertEqual(counts["unsafe_blocks"], 1)

    def test_sys_crates_reads_links_keys(self) -> None:
        from unittest import mock
        meta = {"packages": [
            {"name": "libgit2-sys", "links": "git2",
             "targets": [{"name": "libgit2_sys", "kind": ["lib"]}]},
            {"name": "pcre2-sys", "links": None,
             "targets": [{"name": "pcre2_sys", "kind": ["lib"]}]},
            {"name": "git2", "links": None, "targets": [{"name": "git2", "kind": ["lib"]}]}]}
        done = mock.Mock(returncode=0, stdout=json.dumps(meta))
        with mock.patch("crustify_audit.driver.subprocess.run", return_value=done):
            self.assertEqual(driver.sys_crates(Path("."), ["libc"]), ["libc", "libgit2_sys", "pcre2_sys"])


class PartitionTests(unittest.TestCase):
    def test_driver_carries_no_seam_names(self) -> None:
        src = MAIN_RS.read_text()
        self.assertNotIn("UM_SEAM_FNS", src)
        self.assertFalse([k for k in driver._COUNTS if k.endswith(("_seam", "_smell"))
                          and not k.startswith("ty_wrapper_borrow")])

    def test_raw_and_void_partitions_are_emitted(self) -> None:
        keys, _ = _emission()
        parts = ("ty_pub_fields_pub", "ty_pub_fields_priv", "ty_priv", "fn_pub_safe", "fn_pub_unsafe",
                 "fn_priv_safe", "fn_priv_unsafe")
        for k in ("raw_ptr", "raw_ptr_args", "raw_ptr_rets", "raw_ptr_fields", "void_ptr"):
            self.assertNotIn(k, keys)
        for fam in ("raw_ptr", "void_ptr"):
            for part in parts:
                self.assertIn(f"{fam}_{part}", keys)
                self.assertIn(f"{fam}_{part}", driver.SITE_COUNTERS)
        for k in ("unsafe_fns", "unsafe_fns_pub", "unsafe_fns_priv"):
            self.assertIn(k, keys)

    def test_ffibox_fn_and_ty_families_mirror(self) -> None:
        kinds = [k[len("fn_sig_"):-len("_pub")] for k in driver.FFIBOX_COUNTERS
                 if k.startswith("fn_sig_") and k.endswith("_pub")]
        self.assertEqual(kinds, ["ffibox_owner", "ffibox_handle", "non_ffibox_owner",
                                 "non_ffibox_wrapper_borrow", "non_ffibox_non_wrapper_borrow",
                                 "std_ty_borrow"])
        for k in kinds:
            for name in (f"fn_sig_{k}_priv", f"ty_pub_fields_pub_{k}",
                         f"ty_pub_fields_priv_{k}", f"ty_priv_{k}"):
                self.assertIn(name, driver.FFIBOX_COUNTERS)
        self.assertFalse([k for k in driver.FFIBOX_COUNTERS
                          if "_sig_" in k and not k.startswith("fn_sig_") or k.endswith("_seam")])


if __name__ == "__main__":
    unittest.main()
