"""Tests for the provenance/status report; values stay separate from official contest claims."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_builder():
    spec = importlib.util.spec_from_file_location("build_intelligence", ROOT / "scripts" / "build_intelligence.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IntelligenceReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load_builder()
        cls.report = json.loads((ROOT / "data/intelligence_report.json").read_text())
        cls.competition = json.loads((ROOT / "data/competition_results.json").read_text())

    def test_report_is_deterministic_and_fresh(self):
        self.assertEqual(self.report, self.builder.build_report())
        self.assertTrue(self.report["_meta"]["deterministic"])
        self.assertTrue(self.report["_meta"]["not_a_forecast"])

    def test_provenance_classes_are_explicit(self):
        p = self.report["provenance"]
        self.assertIn("tradingview_official", p)
        self.assertIn("cme_official", p)
        self.assertIn("market_data_vendor", p)
        self.assertIn("repository_simulation", p)
        self.assertGreater(p["market_data_vendor"]["captured_series"], 0)

    def test_every_username_is_reported_once(self):
        users = [u for row in self.report["model_comparison"]["results"] for u in row["usernames"]]
        expected = [p["username"] for p in self.competition["participants"]]
        self.assertEqual(sorted(users), sorted(expected))
        self.assertEqual(len(users), len(set(users)))

    def test_finite_shadow_result_does_not_claim_ten_x(self):
        d = self.report["model_comparison"]["decision"]
        self.assertFalse(d["any_shadow_10x"])
        self.assertFalse(d["any_shadow_20x"])
        self.assertFalse(d["any_shadow_50x"])
        self.assertFalse(d["any_shadow_100x"])
        self.assertIn("forecast", d["interpretation"])


if __name__ == "__main__":
    unittest.main()
