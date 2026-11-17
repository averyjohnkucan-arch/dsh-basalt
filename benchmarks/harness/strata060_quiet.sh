#!/bin/bash
set -euo pipefail
unit=dsh-ninfer1616-build-parallel.service
trap 'systemctl --user thaw "$unit" || true' EXIT
systemctl --user freeze "$unit"
r=/mnt/media/scratch/dsh-inference-tuning-20261115
"$r/tools/build-env/bin/python" "$r/work/strata060_quiet.py"
