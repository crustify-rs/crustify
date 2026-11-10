"""`crustify usage`: one session's usage record, from either CLI's transcript."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import importlib.machinery
import importlib.util
import sys

# The script under test, beside this file: a module without a .py name.
_loader = importlib.machinery.SourceFileLoader(
    "crustify_usage", str(Path(__file__).with_name("crustify-usage")))
_spec = importlib.util.spec_from_loader("crustify_usage", _loader)
cu = importlib.util.module_from_spec(_spec)
sys.modules["crustify_usage"] = cu
_loader.exec_module(cu)
transcript_format, transcript_record = cu.transcript_format, cu.transcript_record

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
            "model": "claude-sonnet-5",
            "input_tokens": 2, "output_tokens": 66, "cache_read_tokens": 10,
            "cache_write_tokens": 0, "cache_write_1h_tokens": 100}])
        self.assertEqual(record["duration_ms"], 11000)

    def test_a_provider_the_transcript_cannot_know(self) -> None:
        path = self.write("a.transcript.jsonl", CLAUDE)
        record = transcript_record(path, backend="claude",
                                   model_proxy="openrouter")
        self.assertEqual((record["provider"], record["model"]),
                         ("openrouter", "claude-sonnet-5"))
        with self.assertRaisesRegex(ValueError, "not a codex one"):
            transcript_record(path, backend="codex")

    def test_a_codex_rollout(self) -> None:
        path = self.write("b.transcript.jsonl", CODEX)
        self.assertEqual(transcript_format(path), "codex")
        record = transcript_record(path)
        self.assertEqual((record["provider"], record["model"]),
                         ("openrouter", "openai/gpt-6.1-sol"))
        self.assertEqual(record["requests"], [{
            "model": "openai/gpt-6.1-sol",
            "input_tokens": 100, "output_tokens": 30, "cache_read_tokens": 20,
            "cache_write_tokens": 0, "cache_write_1h_tokens": 0}])
        self.assertEqual(record["duration_ms"], 120000)

    def test_anything_else_is_refused(self) -> None:
        path = self.write("c.jsonl", [{"hello": "world"}])
        with self.assertRaises(ValueError):
            transcript_format(path)





class _Rates(unittest.TestCase):
    """Transcripts and rate sources the pricing tests share."""

    RATES = {"base": {"input": 1e-6, "output": 2e-6, "cache_read": 1e-7,
                      "cache_write": 1e-6, "cache_write_1h": 2e-6},
             "tiers": []}

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.rates = self.dir / "rates"
        self.claude = self.dir / "a.transcript.jsonl"
        self.claude.write_text("".join(json.dumps(e) + "\n" for e in CLAUDE))
        self.codex = self.dir / "b.transcript.jsonl"
        self.codex.write_text("".join(json.dumps(e) + "\n" for e in CODEX))

    def sources(self, tables: dict):
        """The fetched rates: ``tables`` per provider, every other empty."""
        from unittest import mock
        pricing = cu
        return mock.patch.dict(pricing._SOURCES, {
            p: (lambda p=p: tables.get(p, {})) for p in pricing._SOURCES})

    def report(self, paths, tables, **kw):
        report = cu.report
        with self.sources(tables):
            return report(paths, rates=self.rates, **kw)


class ReportTests(_Rates):
    """The report prices each session request by request, at the rates it
    fetched, and keeps them as a snapshot when they changed."""

    def test_sessions_and_total(self) -> None:
        doc = self.report([self.claude, self.codex],
                          {"anthropic": {"claude-sonnet-5": self.RATES}})
        a, b = doc["sessions"]
        # 2 in, 66 out, 10 cache reads, 100 1h cache writes.
        self.assertAlmostEqual(a["cost_usd"], 2e-6 + 132e-6 + 1e-6 + 200e-6)
        self.assertIsNone(b["cost_usd"])      # openrouter is not in the table
        self.assertEqual(doc["total"]["unpriced_sessions"], 1)
        self.assertEqual(doc["total"]["request_count"], 2)
        self.assertAlmostEqual(doc["total"]["cost_usd"], a["cost_usd"])
        self.assertEqual(a["source"], str(self.claude))
        self.assertEqual(b["requests"][0]["model"], "openai/gpt-6.1-sol")

    def test_a_snapshot_is_kept_only_when_the_rates_change(self) -> None:
        tables = {"anthropic": {"claude-sonnet-5": self.RATES}}
        self.report([self.claude], tables)
        self.report([self.claude], tables)
        self.assertEqual(len(list(self.rates.glob("*.json"))), 1)

    def test_a_run_prices_at_the_rates_it_fetched(self) -> None:
        double = {"base": {k: 2 * v for k, v in self.RATES["base"].items()},
                  "tiers": []}
        first = self.report([self.claude], {"anthropic": {"claude-sonnet-5": self.RATES}})
        second = self.report([self.claude], {"anthropic": {"claude-sonnet-5": double}})
        self.assertAlmostEqual(second["sessions"][0]["cost_usd"],
                               2 * first["sessions"][0]["cost_usd"])
        # A change is a new snapshot, and each report names its own.
        self.assertEqual(len(list(self.rates.glob("*.json"))), 2)
        self.assertIn(second["rates"], {p.stem for p in self.rates.glob("*.json")})
        # A kept snapshot reproduces the costs of the report that named it,
        # whatever the rates are now.
        again = self.report([self.claude], {}, snapshot=first["rates"])
        self.assertEqual(again["sessions"][0]["cost_usd"],
                         first["sessions"][0]["cost_usd"])
        self.assertEqual(again["rates"], first["rates"])
        latest = self.report([self.claude], {}, snapshot="latest")
        self.assertEqual(latest["sessions"][0]["cost_usd"],
                         second["sessions"][0]["cost_usd"])
        with self.assertRaisesRegex(ValueError, "no rate snapshot 19990101"):
            self.report([self.claude], {}, snapshot="19990101T000000Z")

    def test_a_failed_fetch_keeps_the_latest_rates(self) -> None:
        from unittest import mock
        pricing = cu
        self.report([self.claude], {"anthropic": {"claude-sonnet-5": self.RATES}})

        def boom():
            raise OSError("offline")
        with mock.patch.dict(pricing._SOURCES, {p: boom for p in pricing._SOURCES}), \
                mock.patch("sys.stderr"):
            report = cu.report
            doc = report([self.claude], rates=self.rates)
        self.assertIsNotNone(doc["sessions"][0]["cost_usd"])
        # A failure reads as no change: no new snapshot.
        self.assertEqual(len(list(self.rates.glob("*.json"))), 1)

class SessionTests(_Rates):
    """`crustify usage` prices a session as its record says, and records the
    rate snapshot it priced at, which later pricings reuse."""

    def setUp(self) -> None:
        super().setUp()
        self.home = self.dir / "home"
        d = self.home / "sessions" / "s"
        d.mkdir(parents=True)
        self.record = d / "binder.session.json"
        self.record.write_text(json.dumps({
            "agent": "binder", "backend": "claude", "billing": "subscription",
            "model_proxy": None, "args": [], "session_id": "s"}))

    def price(self, tables, **kw):
        price_session = cu.price_session
        with self.sources(tables):
            return price_session("s", self.claude, rates=self.rates,
                                 home=self.home, **kw)

    def test_the_record_names_the_snapshot_and_reuses_it(self) -> None:
        double = {"base": {k: 2 * v for k, v in self.RATES["base"].items()},
                  "tiers": []}
        first = self.price({"anthropic": {"claude-sonnet-5": self.RATES}})
        self.assertEqual(json.loads(self.record.read_text())["rates"], first["rates"])
        # The rates moved, but the session is priced as it was.
        again = self.price({"anthropic": {"claude-sonnet-5": double}})
        self.assertEqual(again["sessions"][0]["cost_usd"],
                         first["sessions"][0]["cost_usd"])
        self.assertEqual(again["session_id"], "s")

    def test_a_named_snapshot_reprices_and_is_recorded(self) -> None:
        self.price({"anthropic": {"claude-sonnet-5": self.RATES}})
        pricing = cu
        double = {"base": {k: 2 * v for k, v in self.RATES["base"].items()},
                  "tiers": []}
        with self.sources({"anthropic": {"claude-sonnet-5": double}}):
            name, _ = pricing.fetch(self.rates)
        doc = self.price({}, snapshot=name)
        self.assertEqual(json.loads(self.record.read_text())["rates"], name)
        self.assertEqual(doc["rates"], name)

    def test_the_proxy_comes_from_the_record(self) -> None:
        record = json.loads(self.record.read_text())
        self.record.write_text(json.dumps(
            {**record, "billing": "api", "model_proxy": "openrouter"}))
        doc = self.price({"openrouter": {"claude-sonnet-5": self.RATES}})
        self.assertEqual(doc["sessions"][0]["provider"], "openrouter")
        self.assertIsNotNone(doc["sessions"][0]["cost_usd"])

    def test_another_sessions_transcript_is_refused(self) -> None:
        price_session = cu.price_session
        with self.assertRaisesRegex(ValueError, "transcript of session s, not t"):
            price_session("t", self.claude, rates=self.rates, home=self.home)

    def test_a_subagent_transcript_names_its_agent(self) -> None:
        sub = self.dir / "agent-a1.jsonl"
        sub.write_text("".join(
            json.dumps({**e, "isSidechain": True, "agentId": "a1"}) + "\n"
            for e in CLAUDE))
        self.assertEqual(cu.transcript_session(sub), "agent-a1")
        with self.assertRaisesRegex(ValueError, "transcript of session agent-a1, not s"):
            cu.price_session("s", sub, rates=self.rates, home=self.home)


if __name__ == "__main__":
    unittest.main()
