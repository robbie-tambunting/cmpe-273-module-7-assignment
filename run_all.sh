#!/usr/bin/env bash
# Runs both demos and the test suite, saving output to evidence/.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p evidence

python3 demo_ordering.py 2>&1 | tee evidence/demo_ordering.txt
echo
python3 demo_fencing.py 2>&1 | tee evidence/demo_fencing.txt
echo
python3 -m unittest discover -s tests -t . -v 2>&1 | tee evidence/tests.txt
