#!/bin/bash
git checkout main
git pull

set -a
source .venv/bin/activate

python -m bot
