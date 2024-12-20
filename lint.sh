#!/bin/sh

black *.py
isort --profile black *.py
flake8 --max-line-length 88 __init__.py _helper.py openlock.py test.py test_openlock.py
mypy test_openlock.py openlock.py --strict --implicit-reexport
mdl *.md
cat README.md | aspell -a --mode=markdown --personal=./ignore.txt |grep \&
