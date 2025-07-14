.PHONY: setup test lint typecheck security docs clean

setup:
	python -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

test:
	. .venv/bin/activate && pytest --maxfail=3 --disable-warnings -q

lint:
	. .venv/bin/activate && flake8 .

typecheck:
	. .venv/bin/activate && mypy .

security:
	. .venv/bin/activate && bandit -r .

docs:
	cd docs && make html

clean:
	rm -rf .venv build dist docs/_build
