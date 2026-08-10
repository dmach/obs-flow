.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

.PHONY: blog
blog: ## Run the MkDocs development server and open the blog in the browser
	(sleep 1 && xdg-open http://127.0.0.1:8080) & uvx --with mkdocs-material mkdocs serve -a 0.0.0.0:8080
