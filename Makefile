.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

.PHONY: reset-db
reset-db: ## Reset the database and recreate migrations
	rm -f packages/server/src/obs_flow_server/db.sqlite3
	find packages/server/src/obs_flow_server/*/migrations -type f -name "*.py" ! -name "__init__.py" -delete
	uv run --package obs-flow-server python packages/server/src/obs_flow_server/manage.py makemigrations
	uv run --package obs-flow-server python packages/server/src/obs_flow_server/manage.py migrate
	uv run --package obs-flow-server python packages/server/src/obs_flow_server/manage.py loaddata packages/server/src/obs_flow_server/core/fixtures/opensuse_data.json
	./flow config git-mapping add --project=openSUSE:Leap:16.1 --owner=openSUSE --repo=Leap --branch=leap-16.1
	./flow config git-mapping add --project=openSUSE:Leap:16.1 --package=osc --owner=pool --repo=osc --branch=leap-16.1
	./flow config review add --project=openSUSE:Leap:16.1 --type=package --user=factory-auto
	./flow config review add --project=openSUSE:Leap:16.1 --type=package --group=opensuse-review-team
	./flow config review add --project=openSUSE:Leap:16.1 --type=package --user=darix
	./flow config review add --project=openSUSE:Leap:16.1 --type=package --role=maintainer
	curl -X POST http://localhost:8000/api/v1/pr/sync -d '{"owner": "pool", "repo": "osc", "number": 4}'

.PHONY: run
run: ## Run the django-bolt server in development mode
	uv run --package obs-flow-server python packages/server/src/obs_flow_server/manage.py runbolt --dev

.PHONY: dbshell
dbshell: ## Open a database shell
	uv run --package obs-flow-server python packages/server/src/obs_flow_server/manage.py dbshell

.PHONY: test
test: ## Run all tests (pytest and Django tests)
	uv run --all-packages pytest
	PYTHONPATH=packages/server/src/obs_flow_server uv run --all-packages python packages/server/src/obs_flow_server/manage.py test accounts core reviews pull_requests staging

.PHONY: completions
completions: ## Generate shell completion scripts for obs-flow-cli
	@mkdir -p packages/cli/completions
	@echo "Generating Bash completion..."
	@_OBS_FLOW_CLI_COMPLETE=bash_source uv run --package obs-flow-cli obs-flow-cli > packages/cli/completions/obs-flow-cli.bash
	@echo "Generating Zsh completion..."
	@_OBS_FLOW_CLI_COMPLETE=zsh_source uv run --package obs-flow-cli obs-flow-cli > packages/cli/completions/obs-flow-cli.zsh
	@echo "Generating Fish completion..."
	@_OBS_FLOW_CLI_COMPLETE=fish_source uv run --package obs-flow-cli obs-flow-cli > packages/cli/completions/obs-flow-cli.fish
