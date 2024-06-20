#!/bin/sh

black *.py
isort --profile black *.py
flake8 --max-line-length 88 _openlock.py test.py
mdl *.md
