#!/usr/bin/env bash
# Prepare-stage verification of the noads fix against pristine upstream files (no substitutes).
# Must run on Linux: this machine's Windows Defender quarantines upstream install.sh,
# which forces the local dry-run to use AV-safe stubs for the four rewritten files.
#
# Scope — this script covers:
#   unit tests, patch dry-run, full prepare.py on ORIGINAL files, generated-tree
#   check.py, whitespace gate, maintenance self-check, provenance and content assertions.
# It does NOT cover (these remain CI-only):
#   npm test / typecheck / build, go test, gitleaks secret scan, 8-platform build.
#
# Usage:
#   CONTROL=/path/to/pr-branch-checkout ./linux-verify.sh
# Environment:
#   CONTROL   checkout of the PR branch of xinian5216/3x-ui-noads (required)
#   TAG       upstream stable tag to verify (default v3.11.0)
#   UPSTREAM  upstream git remote (default https://github.com/MHSanaei/3x-ui.git)
set -euo pipefail

CONTROL="${CONTROL:?set CONTROL to the PR-branch checkout}"
TAG="${TAG:-v3.11.0}"
UPSTREAM="${UPSTREAM:-https://github.com/MHSanaei/3x-ui.git}"
REPOSITORY="xinian5216/3x-ui-noads"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

python3 -m pip install --disable-pip-version-check --quiet PyYAML==6.0.3

echo "== cloning upstream $TAG into $WORK/source =="
git clone --depth 1 --branch "$TAG" "$UPSTREAM" "$WORK/source"
SHA="$(git -C "$WORK/source" rev-parse HEAD)"
echo "tag $TAG -> $SHA"

echo "== [1/7] unit tests (CI step 3 gate) =="
(cd "$CONTROL" && python3 -m unittest discover -s .noads -p 'test_*.py')

echo "== [2/7] patch dry-run on pristine source =="
git -C "$WORK/source" apply --check --verbose "$CONTROL/.noads/noads.patch"

echo "== [3/7] full prepare.py dry-run with ORIGINAL files =="
python3 "$CONTROL/.noads/prepare.py" --source "$WORK/source" --control "$CONTROL" \
  --tag "$TAG" --sha "$SHA" --repository "$REPOSITORY"

echo "== [4/7] advertising/credential check on the prepared tree =="
python3 "$CONTROL/.noads/check.py" --root "$WORK/source" --control "$CONTROL"

echo "== [5/7] whitespace gate =="
git -C "$WORK/source" diff --check && echo "(clean)"

echo "== [6/7] maintenance self-check =="
(cd "$CONTROL" && python3 .noads/check.py --maintenance)

echo "== [7/7] provenance and content assertions =="
CONTROL="$CONTROL" WORK="$WORK" TAG="$TAG" python3 - <<'PY'
import hashlib, json, os, re, sys
from pathlib import Path

control, work, tag = Path(os.environ['CONTROL']), Path(os.environ['WORK']) / 'source', os.environ['TAG']
prov = json.loads((work / '.noads/provenance.json').read_text(encoding='utf-8'))
assert prov['upstream_tag'] == tag, prov['upstream_tag']
assert prov['patch_sha256'] == hashlib.sha256((control / '.noads/noads.patch').read_bytes()).hexdigest()
assert prov['source_transform_sha256'] == hashlib.sha256((control / '.noads/strip_sponsors.py').read_bytes()).hexdigest()

index_go = (work / 'internal/web/controller/index.go').read_text(encoding='utf-8')
assert 'CSRFMiddleware(getRemoteIp)' in index_go and '/sponsors' not in index_go
panel = (work / 'frontend/src/routes/panelRoutes.tsx').read_text(encoding='utf-8')
assert 'SponsorsPage' not in panel and "'/sponsors'" not in panel and 'CrownOutlined' not in panel
palette = (work / 'frontend/src/components/command-palette/CommandPalette.tsx').read_text(encoding='utf-8')
sidebar = (work / 'frontend/src/layouts/AppSidebar.tsx').read_text(encoding='utf-8')
assert "'/sponsors'" not in palette and 'DonateButton' not in sidebar and 'DONATE_URL' not in sidebar
kw = set(re.findall(r"^  '(/[^']+)': \[", palette, flags=re.M))
paths = set(re.findall(r"\{ path: '(/[^']+)',", panel))
assert kw == paths, (sorted(kw), sorted(paths))
assert (work / 'LICENSE').read_bytes() == (control / 'LICENSE').read_bytes(), 'LICENSE changed'
for name in ('install.sh', 'update.sh', 'x-ui.sh', 'internal/web/service/panel/panel.go'):
    text = (work / name).read_text(encoding='utf-8')
    # Same gate as check.py: http(s) upstream URLs only; module import paths stay.
    assert not re.search(r'https://(?:github\.com|raw\.githubusercontent\.com|api\.github\.com/repos)/mhsanaei/3x-ui(?=/)', text, re.I), name
for gone in ('frontend/src/pages/sponsors', 'frontend/src/components/sponsor',
             'frontend/src/api/queries/useSponsorsQuery.ts', 'frontend/src/lib/sponsors.ts',
             'frontend/src/test/sponsors.test.tsx', 'internal/web/service/panel/sponsor.go',
             'internal/web/service/panel/sponsor_test.go'):
    assert not (work / gone).exists(), gone
print('all assertions passed; provenance regenerated for', tag)
PY

# Optional handoff to CI for build and Go tests on this exact prepared v3.11.0 tree.
# The original temporary clone is still always removed by the EXIT trap.
if [[ -n "${PREPARED_OUTPUT:-}" ]]; then
  if [[ -e "$PREPARED_OUTPUT" ]]; then
    echo "PREPARED_OUTPUT already exists: $PREPARED_OUTPUT" >&2
    exit 1
  fi
  mkdir -p "$PREPARED_OUTPUT"
  cp -a "$WORK/source/." "$PREPARED_OUTPUT/"
  echo "PREPARED SOURCE: $PREPARED_OUTPUT"
fi

echo "LINUX VERIFY OK: original-file dry-run, all gates green for $TAG"
