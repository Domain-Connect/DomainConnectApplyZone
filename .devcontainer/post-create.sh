#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

rm -fr .venv
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt -r requirements-test.txt

go install github.com/Domain-Connect/dc-template-linter@latest

git submodule update --init --recursive
