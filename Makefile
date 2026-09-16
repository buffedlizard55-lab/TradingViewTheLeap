.PHONY: verify selftest site all serve clean

all: verify site

verify:
	python3 scripts/verify.py

selftest:
	python3 scripts/verify.py --self-test

site: verify
	python3 scripts/build_site.py

serve: site
	cd site && python3 -m http.server 8000 --bind 0.0.0.0

clean:
	rm -f site/index.html
