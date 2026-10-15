.PHONY: install test unit integration clean

install:
	python -m pip install -r requirements.txt

test:
	mkdir -p reports
	python -m pytest tests

unit:
	mkdir -p reports
	python -m pytest tests --ignore=tests/integration

integration:
	mkdir -p reports
	RUN_S3_TESTS=1 python -m pytest tests/integration

clean:
	rm -rf .pytest_cache .coverage coverage.xml reports/junit.xml
