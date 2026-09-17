#!/usr/bin/env python3
"""Deterministic target arithmetic, NOT a market backtest. Standard library only."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (5, 10, 20, 50, 100)


def load(path):
    return json.loads((ROOT / path).read_text())


def target_profit(balance, multiple):
    if balance <= 0 or multiple <= 1:
        raise ValueError('Positive balance and multiple > 1 required')
    return balance * (multiple - 1)


def required_move_pct(profit, notional):
    if profit < 0 or notional <= 0:
        raise ValueError('Nonnegative profit and positive notional required')
    return 100 * profit / notional


def build():
    cfg = load('data/contest_config.json')
    capacity = load('data/initial_capacity.json')
    completed = [r for r in load('data/verified_explosive_returns.json')['records'] if r['status'] == 'final']
    balance = cfg['starting_balance_virtual_usd']
    targets = []
    for multiple in TARGETS:
        profit = target_profit(balance, multiple)
        targets.append({
            'balance_multiple': multiple,
            'net_profit_pct': 100 * (multiple - 1),
            'required_net_profit_usd': profit,
            'ending_balance_usd': balance * multiple,
            'completed_sample_strictly_above': sum(r['return_multiple'] > multiple for r in completed),
            'completed_sample_at_or_above': sum(r['return_multiple'] >= multiple for r in completed),
            'ideal_initial_20x_fixed_exposure_move_pct': required_move_pct(profit, balance * cfg['futures_leverage_ratio']),
        })
    scenarios = []
    for row in capacity['entries']:
        for target in targets:
            scenarios.append({
                'symbol': row['symbol'],
                'balance_multiple': target['balance_multiple'],
                'initial_contracts': row['max_whole_contracts_at_initial_balance'],
                'initial_notional_usd': row['modeled_initial_notional_usd'],
                'favorable_move_pct_to_equal_target': round(required_move_pct(target['required_net_profit_usd'], row['modeled_initial_notional_usd']), 6),
                'quote_source_id': row['quote_source_id'],
            })
    return {
        '_meta': {
            'kind': 'deterministic_arithmetic_not_backtest',
            'input_snapshot_utc': capacity['_meta']['target_snapshot_utc'],
            'completed_sample_size': len(completed),
            'coverage': '20 selected futures only; not a volatility-ranked or exhaustive opportunity list',
            'source_files': ['data/contest_config.json', 'data/initial_capacity.json', 'data/verified_explosive_returns.json'],
            'assumptions': [
                'Multiple means ending balance divided by starting balance, not profit divided by balance.',
                'Fixed initial whole-contract exposure; no compounding or resizing.',
                'Linear favorable price move; no costs, fills, intraday margin path, roll effects or execution modeled.',
                'Equality reaches a target; strictly over requires additional net profit.',
                'Historical champion-only counts are evidence of occurrence, not estimated success probabilities.',
                'No strategy performance or future returns are measured by this experiment.'
            ]
        },
        'targets': targets,
        'scenarios': scenarios,
    }


if __name__ == '__main__':
    path = ROOT / 'data/target_lab.json'
    path.write_text(json.dumps(build(), indent=2) + '\n')
    print(f'Wrote {path.name}: 5 targets, 100 fixed-exposure scenarios; no backtest results')
