#!/usr/bin/env bash
# Offline smoke test: builds the example profile, checks it, and makes the review copy.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
P="$ROOT/skills/profile-studio/scripts/profile.py"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

python3 "$P" doctor
python3 "$P" new "$WORK/firm" --name "Smoke Test Co"
python3 "$P" build "$WORK/firm" --pages 1,9
python3 "$P" check "$WORK/firm"
python3 "$P" docx "$WORK/firm"

test -s "$WORK/firm/build/smoke-test-co-profile.pdf"
test -s "$WORK/firm/build/smoke-test-co-content-draft-v1.docx"

# a missing photo must still build, with a warning
python3 - "$WORK/firm/profile.json" <<'PY'
import json, sys
p = sys.argv[1]; f = json.load(open(p))
f["pages"][2]["photo"] = "does-not-exist.jpg"
json.dump(f, open(p, "w"), indent=2)
PY
python3 "$P" build "$WORK/firm" --pages 3 | tee "$WORK/out.txt"
grep -q "missing photo: does-not-exist.jpg" "$WORK/out.txt"

# `new` must refuse to overwrite a profile
if python3 "$P" new "$WORK/firm" 2>/dev/null; then echo "new overwrote a profile"; exit 1; fi

echo "SMOKE TEST PASSED"
