#!/bin/bash
set -e

# contents of test_coverage.sh
coverage erase
coverage run -m unittest discover ./test
coverage report -m
coverage html
#open ./htmlcov/index.html
