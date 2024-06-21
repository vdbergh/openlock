#!/bin/sh

black *.py
isort --profile black *.py
flake8 --max-line-length 88 openlock.py test.py util.py
mdl *.md
