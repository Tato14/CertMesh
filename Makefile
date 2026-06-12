# CertMesh developer tasks. On Windows use the PowerShell equivalents in README
# (e.g. `$env:PYTHONPATH="src"; uvicorn app.api:app --reload`).

PY ?= python
export PYTHONPATH := src

.PHONY: install run test eval lint foundry-eval deploy clean

install:        ## install with dev + azure extras
	$(PY) -m pip install -e ".[dev,i18n]"

run:            ## serve the dashboard at http://localhost:8000
	$(PY) -m uvicorn app.api:app --reload --port 8000

test:           ## run the test suite
	$(PY) -m pytest -q

eval:           ## print the evaluation scorecard (CI gate)
	$(PY) -m evals.run_evals

eval-ablation:  ## scorecard + critic ablation (proves the grounding gate is load-bearing)
	$(PY) -m evals.run_evals --ablation

foundry-eval:   ## run the managed Foundry evaluators (needs cloud + azure extra)
	$(PY) -m evals.foundry_eval

lint:           ## ruff
	$(PY) -m ruff check src app evals tests

deploy:         ## build the hosted-agent container image (see deploy/deploy_hosted_agent.md)
	docker build -t certmesh:latest -f deploy/Dockerfile .
	@echo "Image built. Push to ACR and provision a Foundry Hosted Agent — see deploy/deploy_hosted_agent.md"

clean:
	rm -rf .pytest_cache .ruff_cache **/__pycache__ evals/_last_scorecard.json evals/_foundry_eval_rows.jsonl
