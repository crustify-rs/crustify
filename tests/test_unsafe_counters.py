import json
from pathlib import Path
import re
import unittest

from crustify_audit import driver

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
        counts, _, seen = driver._collect_emissions(
            "\n".join([line("a", 2), line("b", 3), line("c_sys", 100)]))
        self.assertEqual(seen, 2)
        self.assertEqual(counts["fns_pub"], 5)
        self.assertEqual(counts["raw_ptr_priv_seam"], 5)


if __name__ == "__main__":
    unittest.main()
