"""Independent arithmetic/coverage tests; no synthetic market performance claims."""
import json
import unittest
from decimal import Decimal
from pathlib import Path

from target_lab import build, required_move_pct, target_profit

ROOT = Path(__file__).resolve().parents[1]


class TargetLabTests(unittest.TestCase):
    def test_profit_is_not_balance(self):
        self.assertEqual(target_profit(250000, 5), 1000000)
        self.assertEqual(target_profit(250000, 100), 24750000)
        self.assertEqual(required_move_pct(1000000, 5000000), 20)
        self.assertEqual(required_move_pct(24750000, 5000000), 495)

    def test_invalid_inputs(self):
        for args in [(0, 5), (-1, 5), (250000, 1)]:
            with self.assertRaises(ValueError):
                target_profit(*args)
        for args in [(1, 0), (1, -1), (-1, 100)]:
            with self.assertRaises(ValueError):
                required_move_pct(*args)

    def test_complete_cross_product(self):
        result = build()
        capacity = json.loads((ROOT / 'data/initial_capacity.json').read_text())['entries']
        expected = {(r['symbol'], t) for r in capacity for t in (5, 10, 20, 50, 100)}
        actual = [(r['symbol'], r['balance_multiple']) for r in result['scenarios']]
        self.assertEqual(len(actual), 100)
        self.assertEqual(set(actual), expected)

    def test_every_scenario_independently(self):
        for r in build()['scenarios']:
            profit = Decimal(250000) * (r['balance_multiple'] - 1)
            move = profit * 100 / Decimal(str(r['initial_notional_usd']))
            self.assertAlmostEqual(float(move), r['favorable_move_pct_to_equal_target'], places=5)

    def test_champion_counts_exclude_live(self):
        records = json.loads((ROOT / 'data/verified_explosive_returns.json').read_text())['records']
        for target in build()['targets']:
            # Recompute from published percentages rather than stored multiples.
            n = sum(r['status'] == 'final' and Decimal(str(r['net_profit_pct_as_published'])) >
                    100 * (target['balance_multiple'] - 1) for r in records)
            self.assertEqual(target['completed_sample_strictly_above'], n)
        self.assertEqual(build()['targets'][-1]['completed_sample_strictly_above'], 0)

    def test_artifact_freshness(self):
        self.assertEqual(json.loads((ROOT / 'data/target_lab.json').read_text()), build())

    def test_site_coverage(self):
        html = (ROOT / 'index.html').read_text()
        section = html.split('<section id="targets">')[1].split('</section>')[0]
        self.assertEqual(section.count('<tr>'), 107)  # 2 headers + 5 targets + 100 scenarios
        self.assertIn('not a backtest', section)
        self.assertIn('AUDIT-2026-09-17.md', section)


if __name__ == '__main__':
    unittest.main()
