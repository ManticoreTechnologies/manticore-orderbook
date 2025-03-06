.PHONY: install dev-install test benchmark clean build docs

# Default target
all: test

# Install the package
install:
	pip3 install .

# Install the package in development mode
dev-install:
	pip3 install -e ".[dev]"

# Run tests
test:
	pytest manticore_orderbook/tests/

# Run specific test
test-file:
	pytest $(file)

# Run benchmark
benchmark:
	pip3 install -e ".[benchmark]"
	python3 benchmark.py

# Clean build files
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -name __pycache__ -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name ".pytest_cache" -type d -exec rm -rf {} +

# Build distribution packages
build: clean
	python3 -m build

# Install the package in development mode with benchmark dependencies
bench-install:
	pip3 install -e ".[benchmark]"

# Run tests with coverage
test-cov:
	pytest --cov=manticore_orderbook manticore_orderbook/tests/

# Generate HTML coverage report
coverage-html: test-cov
	coverage html
	@echo "HTML coverage report generated in htmlcov/"

help:
	@echo "Manticore OrderBook Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  all           Run tests (default)"
	@echo "  install       Install the package"
	@echo "  dev-install   Install the package in development mode with testing dependencies"
	@echo "  test          Run all tests"
	@echo "  test-file     Run a specific test file (usage: make test-file file=path/to/test.py)"
	@echo "  test-cov      Run tests with coverage"
	@echo "  coverage-html Generate HTML coverage report"
	@echo "  benchmark     Run performance benchmarks"
	@echo "  bench-install Install with benchmark dependencies"
	@echo "  clean         Remove build artifacts"
	@echo "  build         Build distribution packages" 