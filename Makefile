# Makefile - Development and packaging helpers for AutoPull.

SHELL := /bin/bash

.PHONY: install test lint deb clean

install:
	sudo bash scripts/setup.sh

test:
	pytest -q

lint:
	flake8 autopull tests

deb:
	dpkg-buildpackage -us -uc -b

clean:
	rm -rf build dist .pytest_cache __pycache__
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
	rm -rf debian/autopull debian/.debhelper debian/files
