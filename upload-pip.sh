#!/usr/bin/env bash

rm -Rf ./dist && \
    python setup.py sdist bdist_wheel && \
    twine upload dist/*