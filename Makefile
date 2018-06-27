all_targets: lint test

lint:
	flake8 *.py
	flake8 ./spidy/*.py

test:
	python3 ./spidy/tests.py

help:
	@echo "    lint"
	@echo "        Check PEP8 compliance with flake8."
	@echo "    test"
	@echo "        Run all tests in spidy/tests.py."
