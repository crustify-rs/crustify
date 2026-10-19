"""`crustify usage`: one session's usage record, from either CLI's transcript."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from crustify.core.usage import transcript_format, transcript_record

CLAUDE = [
    {"type": "user", "sessionId": "s", "timestamp": "2026-10-19T19:03:10.000Z",
     "message": {"role": "user", "content": "hi"}},
    {"type": "assistant", "sessionId": "s", "timestamp": "2026-10-19T19:03:20.000Z",
     "message": {"id": "m1", "model": "claude-sonnet-5", "usage": {
         "input_tokens": 2, "output_tokens": 66, "cache_read_input_tokens": 10,
         "cache_creation": {"ephemeral_5m_input_tokens": 0,
                            "ephemeral_1h_input_tokens": 100}}}},
    # The transcript repeats a message; it counts once.
    {"type": "assistant", "sessionId": "s", "timestamp": "2026-10-19T19:03:21.000Z",
     "message": {"id": "m1", "model": "claude-sonnet-5", "usage": {
         "input_tokens": 2, "output_tokens": 66}}},
]
CODEX = [
    {"type": "session_meta", "timestamp": "2026-10-11T09:40:00Z",
     "payload": {"id": "r", "model_provider": "openrouter"}},
    {"type": "turn_context", "timestamp": "2026-10-11T09:40:01Z",
     "payload": {"model": "openai/gpt-6.1-sol"}},
    {"type": "event_msg", "timestamp": "2026-10-11T09:41:00Z",
     "payload": {"type": "token_count", "info": {
         "total_token_usage": {"total_tokens": 150},
         "last_token_usage": {"input_tokens": 120, "cached_input_tokens": 20,
                              "output_tokens": 30}}}},
    # A re-emitted count, with no new request: skipped.
    {"type": "event_msg", "timestamp": "2026-10-11T09:42:00Z",
     "payload": {"type": "token_count", "info": {
         "total_token_usage": {"total_tokens": 150},
         "last_token_usage": {"input_tokens": 120, "cached_input_tokens": 20,
                              "output_tokens": 30}}}},
]


class UsageTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def write(self, name: str, events: list[dict]) -> Path:
        path = self.dir / name
        path.write_text("".join(json.dumps(e) + "\n" for e in events))
        return path

    def test_a_claude_transcript(self) -> None:
        path = self.write("a.transcript.jsonl", CLAUDE)
        self.assertEqual(transcript_format(path), "claude")
        record = transcript_record(path)
        self.assertEqual((record["provider"], record["model"]),
                         ("anthropic", "claude-sonnet-5"))
        self.assertEqual(record["requests"], [{
            "input_tokens": 2, "output_tokens": 66, "cache_read_tokens": 10,
            "cache_write_tokens": 0, "cache_write_1h_tokens": 100}])
        self.assertEqual(record["duration_ms"], 11000)

    def test_a_provider_the_transcript_cannot_know(self) -> None:
        path = self.write("a.transcript.jsonl", CLAUDE)
        record = transcript_record(path, provider="openrouter",
                                   model="anthropic/claude-sonnet-5")
        self.assertEqual((record["provider"], record["model"]),
                         ("openrouter", "anthropic/claude-sonnet-5"))

    def test_a_codex_rollout(self) -> None:
        path = self.write("b.transcript.jsonl", CODEX)
        self.assertEqual(transcript_format(path), "codex")
        record = transcript_record(path)
        self.assertEqual((record["provider"], record["model"]),
                         ("openrouter", "openai/gpt-6.1-sol"))
        self.assertEqual(record["requests"], [{
            "input_tokens": 100, "output_tokens": 30, "cache_read_tokens": 20,
            "cache_write_tokens": 0, "cache_write_1h_tokens": 0}])
        self.assertEqual(record["duration_ms"], 120000)

    def test_anything_else_is_refused(self) -> None:
        path = self.write("c.jsonl", [{"hello": "world"}])
        with self.assertRaises(ValueError):
            transcript_format(path)


if __name__ == "__main__":
    unittest.main()


class ReportTests(unittest.TestCase):
    """The report prices each session request by request, and fetches the
    rates again only for a model the cache does not know."""

    RATES = {"base": {"input": 1e-6, "output": 2e-6, "cache_read": 1e-7,
                      "cache_write": 1e-6, "cache_write_1h": 2e-6},
             "tiers": []}

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.claude = self.dir / "a.transcript.jsonl"
        self.claude.write_text("".join(json.dumps(e) + "\n" for e in CLAUDE))
        self.codex = self.dir / "b.transcript.jsonl"
        self.codex.write_text("".join(json.dumps(e) + "\n" for e in CODEX))

    def report(self, paths, tables):
        from unittest import mock
        from crustify.usage import report
        calls = []

        def load_prices(*, refresh=False):
            calls.append(refresh)
            return tables[refresh]
        with mock.patch("crustify.usage.load_prices", side_effect=load_prices):
            return report(paths), calls

    def test_sessions_and_total(self) -> None:
        known = {"anthropic": {"claude-sonnet-5": self.RATES}}
        doc, calls = self.report([self.claude, self.codex],
                                 {False: known, True: known})
        a, b = doc["sessions"]
        # 2 in, 66 out, 10 cache reads, 100 1h cache writes.
        self.assertAlmostEqual(a["cost_usd"], 2e-6 + 132e-6 + 1e-6 + 200e-6)
        self.assertIsNone(b["cost_usd"])      # openrouter is not in the table
        self.assertEqual(doc["total"]["unpriced_sessions"], 1)
        self.assertEqual(doc["total"]["request_count"], 2)
        self.assertAlmostEqual(doc["total"]["cost_usd"], a["cost_usd"])
        self.assertEqual(a["source"], str(self.claude))
        self.assertEqual(calls, [False, True])  # one refetch, for the unknown

    def test_a_known_model_needs_no_fetch(self) -> None:
        known = {"anthropic": {"claude-sonnet-5": self.RATES}}
        _, calls = self.report([self.claude], {False: known, True: {}})
        self.assertEqual(calls, [False])

    def test_a_new_model_is_priced_after_a_refetch(self) -> None:
        doc, calls = self.report(
            [self.claude], {False: {}, True: {"anthropic": {"claude-sonnet-5": self.RATES}}})
        self.assertEqual(calls, [False, True])
        self.assertIsNotNone(doc["sessions"][0]["cost_usd"])


class PriceCacheTests(unittest.TestCase):
    def test_a_failed_refetch_keeps_the_cached_rates(self) -> None:
        from unittest import mock
        from crustify.core import pricing
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "prices.json"
            cache.write_text(json.dumps({"openrouter": {"m": {
                "base": {"input": 1e-6}, "tiers": []}}}))

            def boom():
                raise OSError("offline")
            with mock.patch.dict(pricing._SOURCES, {p: boom for p in pricing._SOURCES}), \
                    mock.patch("sys.stderr"):
                prices = pricing.load_prices(str(cache), refresh=True)
        self.assertIn("m", prices["openrouter"])


if __name__ == "__main__":
    unittest.main()
