.PHONY: all verify selftest site serve clean check backtest capture

all: check

# Full gate, mirroring what CI runs.
check: verify site freshness

verify:
	python3 scripts/verify.py

backtest:
	python3 scripts/run_backtests.py

capture:
	python3 scripts/fetch_market_data.py

selftest:
	python3 scripts/verify.py --self-test

site:
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
