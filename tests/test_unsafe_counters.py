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
        for k in ("unsafe_fns_pub_seam", "unsafe_fns_priv_seam", "fns_pub", "fns_priv",
                  "raw_ptr_pub_seam", "raw_ptr_priv_seam", "raw_ptr_pub", "raw_ptr_priv"):
            self.assertIn(k, keys)
            self.assertIn(k, driver.SITE_COUNTERS)

    def test_new_counts_sum_across_crates(self) -> None:
        line = lambda crate, n: json.dumps(
            {"crate": crate, "unsafe_blocks": 0, "fns_pub": n, "raw_ptr_priv_seam": n, "sites": {}})
        counts, _, seen, _ = driver._collect_emissions(
            "\n".join([line("a", 2), line("b", 3), line("c_sys", 100)]))
        self.assertEqual(seen, 2)
        self.assertEqual(counts["fns_pub"], 5)
        self.assertEqual(counts["raw_ptr_priv_seam"], 5)


class FfiboxTests(unittest.TestCase):
    def test_counters_match_the_driver_in_order(self) -> None:
        src = MAIN_RS.read_text()
        body = re.search(r"const FFIBOX_COUNTERS: &\[&str\] = &\[(.*?)\];", src, re.S).group(1)
        self.assertEqual(tuple(re.findall(r'"(\w+)"', body)), driver.FFIBOX_COUNTERS)

    def test_breakdowns_merge_across_crates_and_skip_sys(self) -> None:
        line = lambda crate, n: json.dumps({
            "crate": crate,
            "ffibox": {"ffibox_sig_owners_pub": {"CBox": n}, "drop_impl": {"crate::Owner": 1}},
            "sites": {"ffibox_sig_owners_pub": [{"file": "a.rs", "count": n, "lines": [1]}]}})
        _, sites, seen, ffibox = driver._collect_emissions(
            "\n".join([line("a", 2), line("b", 3), line("c_sys", 100)]))
        # an ffibox line is not a metrics line
        self.assertEqual(seen, 0)
        self.assertEqual(ffibox["ffibox_sig_owners_pub"], {"CBox": 5})
        self.assertEqual(ffibox["drop_impl"], {"crate::Owner": 2})
        self.assertEqual(ffibox["ffibox_sig_handles_priv"], {})
        self.assertEqual(sum(r["count"] for r in sites["ffibox_sig_owners_pub"]), 5)

    def test_record_totals_every_counter(self) -> None:
        rec = unsafe_scan._ffibox_record({"ffibox_sig_handles_pub": {"Ref": 4, "Mut": 1}})
        self.assertEqual(set(rec["counts"]), set(driver.FFIBOX_COUNTERS))
        self.assertEqual(rec["counts"]["ffibox_sig_handles_pub"], 5)
        self.assertEqual(rec["counts"]["ffibox_sig_owners_pub"], 0)
        self.assertIsNone(unsafe_scan._ffibox_record(None))

    def test_ffibox_sites_need_the_flag(self) -> None:
        with self.assertRaises(SystemExit) as e:
            unsafe_scan.site_counters(["ffibox_sig_owners_pub"])
        self.assertIn("--ffibox", str(e.exception))
        self.assertEqual(unsafe_scan.site_counters(["ffibox_sig_owners_pub"], ffibox=True),
                         ["ffibox_sig_owners_pub"])
        self.assertNotIn("ffibox_sig_owners_pub", unsafe_scan.site_counters(["all"]))
        self.assertIn("ffibox_sig_owners_pub", unsafe_scan.site_counters(["all"], ffibox=True))


class SeamTests(unittest.TestCase):
    def test_driver_carries_no_seam_names_of_its_own(self) -> None:
        src = MAIN_RS.read_text()
        self.assertNotIn("const SEAM_FNS", src)
        self.assertIn('"UM_SEAM_FNS"', src)

    def test_seam_files_are_exact_names_per_line(self) -> None:
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as d:
            a, b = Path(d, "a.txt"), Path(d, "b.txt")
            a.write_text("# ffibox\nas_ptr\n\nfrom_raw  # adopt\n")
            b.write_text("wrap\nas_ptr\n")
            self.assertEqual(unsafe_scan.seam_names([str(a), str(b)]),
                             ["as_ptr", "from_raw", "wrap"])
            Path(d, "g.txt").write_text("wrap_with_*\n")
            with self.assertRaises(SystemExit) as e:
                unsafe_scan.seam_names([str(Path(d, "g.txt"))])
            self.assertIn("no globs", str(e.exception))
        self.assertEqual(unsafe_scan.seam_names(None), [])

    def test_shipped_seam_files_parse_and_do_not_overlap(self) -> None:
        repo = Path(driver.__file__).resolve().parents[2]
        crustify = unsafe_scan.seam_names([str(repo / "docs/translate/seams.txt")])
        self.assertEqual(crustify, ["to_raw"])
        ffibox = repo.parent / "ffibox" / "seams.txt"
        if ffibox.is_file():
            self.assertFalse(set(crustify) & set(unsafe_scan.seam_names([str(ffibox)])))


if __name__ == "__main__":
    unittest.main()
