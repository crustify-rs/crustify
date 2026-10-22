"""Every role prompt carries crustify's identity, read from specs/identity.md."""
from __future__ import annotations

import re
import unittest

from crustify import deps
from crustify.agents.base import _PKG_ROOT, expand_includes

IDENTITY = deps.CHECKOUT / "specs" / "identity.md"


class IdentityTests(unittest.TestCase):
    def test_identity_names_the_account_and_email(self) -> None:
        text = IDENTITY.read_text()
        self.assertIn("`crustify-ai`", text)
        self.assertRegex(text, r"crustify <[^>]+@[^>]+>")

    def test_every_role_prompt_includes_it(self) -> None:
        prompts = sorted((_PKG_ROOT / "prompts").glob("*.md"))
        self.assertTrue(prompts)
        identity = IDENTITY.read_text().strip()
        for path in prompts:
            with self.subTest(prompt=path.name):
                raw = path.read_text()
                self.assertEqual(raw.count("<!-- INCLUDE specs/identity.md -->"), 1)
                self.assertNotRegex(raw, r"(?m)^Your git entity:")
                # Formatting the expanded prompt restores the document verbatim.
                rendered = expand_includes(raw).replace("{{", "{").replace("}}", "}")
                self.assertIn(identity, rendered)


if __name__ == "__main__":
    unittest.main()
