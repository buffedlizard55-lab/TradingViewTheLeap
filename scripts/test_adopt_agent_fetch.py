"""Synthetic end-to-end test for scripts/adopt_agent_fetch.py (never touches real data/).

Runs inside `python3 -m unittest discover -s scripts -p 'test_*.py'` like every other
suite here. It builds a fake vendor response (with the page-fetch proxy's markdown fence),
adopts it through the real script into a scratch index/out-dir, then loads the produced
canonical capture back through the project's own validated loader.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SCRATCH = os.path.join(ROOT, "scratch", "agent_fetch_test")


def _load_intraday_module():
    """Load intel/intraday.py without putting intel/ on sys.path.

    intel/calendar.py intentionally shadows nothing here: adding intel/ itself to
    sys.path would make `import calendar` (used by the stdlib _strptime) resolve to
    the project's NYSE calendar module and break datetime parsing repo-wide.
    """
    spec = importlib.util.spec_from_file_location(
        "intel_intraday_under_test", os.path.join(ROOT, "intel", "intraday.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AdoptAgentFetchTests(unittest.TestCase):
    def setUp(self):
        os.makedirs(os.path.join(SCRATCH, "responses"), exist_ok=True)
        os.makedirs(os.path.join(SCRATCH, "out"), exist_ok=True)
        doc = {
            "chart": {
                "result": [{
                    "meta": {
                        "currency": "USD", "symbol": "PLUG", "exchangeName": "PCX",
                        "fullExchangeName": "NYSE American", "instrumentType": "EQUITY",
                        "firstTradeDate": 1256819400, "regularMarketTime": 1452870000,
                        "dataGranularity": "1d", "range": "",
                        "timezoneName": "America/New_York",
                        "exchangeTimezoneName": "America/New_York", "gmtoffset": -18000,
                        "shortName": "Plug Power Inc.",
                    },
                    # 4th bar has null volume -> kept with volume 0; 5th bar is the vendor's
                    # appended live tail outside the requested window -> must be dropped.
                    "timestamp": [1451917800, 1452004200, 1452090600, 1452177000,
                                  1489645800],
                    "indicators": {"quote": [{
                        "open":   [2.10, 2.06, 2.03, 1.90, 1.70],
                        "high":   [2.10, 2.11, 2.05, 2.01, 1.75],
                        "low":    [1.96, 2.03, 1.99, 1.90, 1.66],
                        "close":  [2.10, 2.03, 2.03, 1.90, 1.72],
                        "volume": [2057600, 1500000, 1600000, None, 999999],
                    }]},
                    "adjclose": [{"adjclose": [2.10, 2.03, 2.03, 1.90, 1.72]}],
                }],
                "error": None,
            }
        }
        with open(os.path.join(SCRATCH, "responses", "1451606400_1452988800.json"),
                  "w") as fh:
            fh.write("```json\n" + json.dumps(doc) + "\n```")  # proxy fence on purpose
        shutil.copy(os.path.join(ROOT, "data", "intraday_index.json"),
                    os.path.join(SCRATCH, "index.json"))

    def tearDown(self):
        shutil.rmtree(SCRATCH, ignore_errors=True)
        # Keep the scratch root out of the working tree if it is now empty.
        parent = os.path.dirname(SCRATCH)
        if os.path.isdir(parent) and not os.listdir(parent):
            os.rmdir(parent)

    def test_end_to_end(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", "adopt_agent_fetch.py"),
             "--symbol", "PLUG", "--interval", "1d",
             "--responses", "scratch/agent_fetch_test/responses",
             "--index", "scratch/agent_fetch_test/index.json",
             "--out-dir", "scratch/agent_fetch_test/out"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

        intraday = _load_intraday_module()
        index = json.load(open(os.path.join(SCRATCH, "index.json")))
        rec = next(c for c in index["captures"]
                   if c["symbol"] == "PLUG" and c["interval"] == "1d")
        self.assertEqual(rec["status"], "captured")
        self.assertEqual(rec["transport"], "arena-fetch-page")
        self.assertEqual(rec["bar_count"], 4)
        self.assertEqual(rec["chunks"], 1)
        self.assertEqual(rec["chunk_provenance"][0]["bars_dropped_out_of_window"], 1)
        self.assertIn("agent_proxy_note", index["_meta"])

        capture = intraday.load_capture(rec, rel_dir="scratch/agent_fetch_test/out")
        bars = [[b.ts, b.open, b.high, b.low, b.close, b.volume] for b in capture.bars]
        self.assertEqual(bars, [
            [1451917800, 2.1, 2.1, 1.96, 2.1, 2057600],
            [1452004200, 2.06, 2.11, 2.03, 2.03, 1500000],
            [1452090600, 2.03, 2.05, 1.99, 2.03, 1600000],
            [1452177000, 1.9, 2.01, 1.9, 1.9, 0],
        ])


if __name__ == "__main__":
    unittest.main()
