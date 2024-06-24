#!/bin/sh

VERSION=`fgrep __version__ openlock.py  |cut -d ' ' -f 3 | tr -d '"'`

pip install build
python -m build
pip install -I dist/openlock-$VERSION*whl
