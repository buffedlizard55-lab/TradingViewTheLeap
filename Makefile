.PHONY: all verify selftest site serve clean check backtest competition capture refresh placement intraday stocks tvbench exec derived

all: check

# Full gate, mirroring what CI runs.
check: verify site freshness

verify:
	python3 scripts/verify.py

backtest:
	python3 scripts/run_backtests.py

# Re-run the shadow competition from the raw captures (deterministic given --stamp).
competition:
	python3 scripts/run_competition.py --stamp "$$(python3 -c "import json;print(json.load(open('data/competition_results.json'))['_meta']['generated_utc'])")"

capture:
	python3 scripts/fetch_market_data.py

# Re-derive all downstream artifacts after the raw captures change (backtests,
# volatility screen, models.json sync, site rebuild). Run this after `capture`.
refresh:
	python3 scripts/refresh_artifacts.py

selftest:
	python3 scripts/verify.py --self-test
	python3 -m unittest discover -s scripts -p "test_*.py" -v

# Re-derive the placement/prize arithmetic from contest config + captures.
placement:
	python3 scripts/leaderboard_lab.py

# Intraday captures -> measured gap-fill + execution-latency study.
intraday:
	python3 scripts/run_intraday_study.py

# 20-stock volatile pool: our own multi-season paper division (futures roster untouched).
stocks:
	python3 scripts/run_stock_competition.py

# Pine broker-emulator vs Python fill benchmark (blocked while no real export is committed).
tvbench:
	python3 scripts/tv_benchmark.py

# Mechanical "what would be placed next" table rendered at the top of the site.
exec:
	python3 scripts/build_exec_summary.py

# Everything downstream of every capture, in dependency order, skipping absent inputs.
derived:
	python3 scripts/refresh_artifacts.py

site:
	python3 scripts/target_lab.py
	python3 scripts/leaderboard_lab.py
	python3 scripts/build_site.py

# Fail if index.html is not in sync with the data it was rendered from.
freshness: site
	@git diff --quiet -- index.html || { \
	  echo "index.html is stale. Run 'python3 scripts/build_site.py' and commit."; \
	  git diff --stat -- index.html; exit 1; }
	@echo "index.html is in sync with data/ and research/."

serve: site
	python3 -m http.server 8000 --bind 0.0.0.0

clean:
	rm -f index.html .nojekyll

# Free official-provider research route. Exits blocked (2) if secrets unavailable.
# No third-party relay, no paid data, and no replacement of legacy artifacts.
.PHONY: official-bars
official-bars:
	python3 scripts/fetch_official_bars.py
	python3 scripts/run_intraday_study.py --index data/official_bars/index.json --out data/official_bars/study.json
	python3 scripts/run_stock_competition.py --index data/official_bars/index.json --out data/official_bars/competition.json

# Official (Alpaca IEX) vs vendor (Yahoo) close comparison with a split-step detector.
# Needs both data/official_bars/index.json and data/intraday_index.json; exits 2 otherwise.
.PHONY: spot-check
spot-check:
	python3 scripts/spot_check_official_vs_vendor.py

# Merge per-symbol partial indexes produced by capture-intraday-matrix.yml (offline).
.PHONY: merge-intraday
merge-intraday:
	python3 scripts/merge_intraday_indexes.py --partials-dir partials_flat
