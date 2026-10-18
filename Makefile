.DEFAULT_GOAL := help

PYTHON_VERSION ?= 3.14

PLANTUML_VERSION ?= 1.2026.8
PLANTUML_SHA256 ?= 5e1ecfa8ecd32c90b03bbf3b1eb6f020943f98ab0fcf4032be31a0002ee2c462
PLANTUML_URL ?= https://github.com/plantuml/plantuml/releases/download/v$(PLANTUML_VERSION)/plantuml-$(PLANTUML_VERSION).jar
PLANTUML_JAR ?= .tools/plantuml-$(PLANTUML_VERSION).jar

help: ## list every target with its description
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-10s %s\n", $$1, $$2}'

setup: ## create the uv virtual environment and install dependencies
	uv venv --python $(PYTHON_VERSION)
	uv pip install weasyprint beautifulsoup4 tqdm pypdf

run: ## convert ./emails.mbox into ./emails_combined.pdf, ARGS="-i x -o y" to override
	uv run --no-project --python .venv main.py $(ARGS)

diagrams: ## render every docs/diagrams/*.puml to a committed PNG beside it
	@set -e; \
	if [ ! -f "$(PLANTUML_JAR)" ] || ! echo "$(PLANTUML_SHA256)  $(PLANTUML_JAR)" | sha256sum -c --status -; then \
	  mkdir -p $(patsubst %/,%,$(dir $(PLANTUML_JAR))); \
	  curl -fsSL "$(PLANTUML_URL)" -o "$(PLANTUML_JAR)"; \
	fi; \
	echo "$(PLANTUML_SHA256)  $(PLANTUML_JAR)" | sha256sum -c -; \
	if ! java -version >/dev/null 2>&1; then \
	  echo "diagrams: java not found; docker fallback: docker run --rm -v $$(pwd):/w -w /w/docs/diagrams plantuml/plantuml:$(PLANTUML_VERSION) -tpng '*.puml'"; \
	  exit 1; \
	fi; \
	java -jar "$(PLANTUML_JAR)" -failfast2 -overwrite -tpng docs/diagrams/*.puml; \
	for src in docs/diagrams/*.puml; do \
	  png="$${src%.puml}.png"; \
	  if [ ! -f "$$png" ]; then echo "diagrams: render failed for $$src"; exit 1; fi; \
	done

clean: ## remove the virtual environment and run leftovers
	rm -rf .venv
	rm -f emails_combined.pdf
