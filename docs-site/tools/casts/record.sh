#!/bin/bash
# Re-record the terminal casts in docs-site/static/casts/. Run on Linux (or WSL) with asciinema and python3-venv:
#   bash docs-site/tools/casts/record.sh
# A private mount namespace puts a throwaway home at /home/you, so no real user or host names are recorded.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
out="$here/../../static/casts"
rm -rf /tmp/mpfdemo && mkdir -p /tmp/mpfdemo/homes/you /tmp/mpfdemo/out
unshare -rm sh -c "mount --bind /tmp/mpfdemo/homes /home && python3 '$here/driver.py' /tmp/mpfdemo/out"
python3 "$here/driver.py" --trim /tmp/mpfdemo/out/*.cast
cp /tmp/mpfdemo/out/*.cast "$out/"
