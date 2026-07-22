.PHONY: run demo persist test lint clean

# Default: a clean 4-cycle demo so compounding self-growth is unmistakable.
run:
	python -m viralworks --fresh --cycles 4

# Longer showcase over more cycles.
demo:
	python -m viralworks --fresh --cycles 6

# Persisted run (does NOT wipe the store) — proves memory survives across runs.
persist:
	python -m viralworks --cycles 1

test:
	python -m pytest -q

clean:
	rm -rf data reports playbooks
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
