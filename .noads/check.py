"""Gate source, secret scan results, and compiled frontend before release."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from clean_docs import check_docs
from preserve import verify_control

def finding_key(root, finding):
    name = finding['File'].replace('\\', '/')
    p = Path(name)
    if p.is_absolute():
        p = p.relative_to(root)
    elif name.startswith(str(root).replace('\\', '/') + '/'):
        p = Path(name[len(str(root)) + 1:])
    elif not (root / p).is_file():
        # Gitleaks may prefix relative findings with its invocation directory.
        candidate = p.resolve()
        if not candidate.is_relative_to(root.resolve()):
            raise ValueError('Credential finding escapes the scanned source')
        p = candidate.relative_to(root.resolve())
    lines = (root / p).read_text(encoding='utf-8', errors='replace').splitlines()
    context = '\n'.join(lines[finding['StartLine'] - 1:finding['EndLine']])
    return {'rule': finding['RuleID'], 'file': p.as_posix(), 'context_sha256': hashlib.sha256(context.encode()).hexdigest()}

def check(root, report=None, built=False, control=None, maintenance=False):
    root = root.resolve()
    if maintenance and (built or report is not None or control is not None):
        raise ValueError('--maintenance is only for maintenance repository self-checks')
    check_docs(root)
    if not (root / 'AGENTS.md').is_file():
        raise ValueError('Downstream AGENTS.md is missing')
    if control:
        verify_control(root, control.resolve())
    provenance = json.loads((root / '.noads/provenance.json').read_text(encoding='utf-8'))
    # Already-published v3.10.0 remains valid while the revised release is prepared.
    transform_hash = provenance.get('source_transform_sha256')
    if transform_hash:
        transform = root / '.noads/strip_sponsors.py'
        # The maintenance repo carries the next transform while its provenance still
        # names the last published release; generated trees keep the strict hash gate.
        if not maintenance and hashlib.sha256(transform.read_bytes()).hexdigest() != transform_hash:
            raise ValueError('Advertising transform does not match source provenance')
        for file in (root / 'frontend/src').rglob('*'):
            if file.suffix not in ('.ts', '.tsx') or 'generated' in file.parts:
                continue
            text = file.read_text(encoding='utf-8')
            if re.search(r'SponsorSlot|SponsorsPage|DonateButton|menu\.(?:sponsors|donate)|[\'"]/sponsors|(?:sponsors|donate)\.sanaei\.dev', text):
                raise ValueError('Advertising integration remains: ' + str(file.relative_to(root)))
        for file in (root / 'internal/web/translation').glob('*.json'):
            data = json.loads(file.read_text(encoding='utf-8'))
            if any(k in data.get('menu', {}) for k in ('sponsors', 'donate')) or 'sponsors' in data.get('pages', {}):
                raise ValueError('Advertising translation keys remain: ' + file.name)
    for name in ('frontend/src/components/sponsor', 'frontend/src/pages/sponsors',
                 'frontend/src/api/queries/useSponsorsQuery.ts', 'internal/web/service/panel/sponsor.go'):
        if (root / name).exists():
            raise ValueError('Advertising source unexpectedly exists: ' + name)
    for name in ('frontend/src/routes.tsx', 'frontend/src/layouts/AppSidebar.tsx',
                 'frontend/src/pages/index/IndexPage.tsx', 'frontend/src/pages/login/LoginPage.tsx',
                 'internal/web/controller/index.go'):
        text = (root / name).read_text(encoding='utf-8')
        if re.search(r'SponsorSlot|SponsorsPage|[\'"]/sponsors|sponsors\.sanaei\.dev', text):
            raise ValueError('Advertising entry point remains: ' + name)
    upstream_url = re.compile(r'https://(?:github\.com|raw\.githubusercontent\.com|api\.github\.com/repos)/mhsanaei/3x-ui(?=/)', re.I)
    for name in ('install.sh', 'update.sh', 'x-ui.sh', 'internal/web/service/panel/panel.go'):
        if upstream_url.search((root / name).read_text(encoding='utf-8')):
            raise ValueError('Updater still uses the official advertising build: ' + name)
    for file in (root / 'internal').rglob('*.go'):
        if 'sponsors.sanaei.dev' in file.read_text(encoding='utf-8'):
            raise ValueError('Remote sponsor host remains in backend source')
    if report:
        baseline = json.loads((root / '.noads/gitleaks-baseline.json').read_text())
        allowed = {json.dumps(f, sort_keys=True) for f in baseline}
        findings = json.loads(report.read_text())
        unexpected = [f for f in findings if json.dumps(finding_key(root, f), sort_keys=True) not in allowed]
        if unexpected:
            # Only identifiers are reported; no finding text or candidate secret is printed.
            for item in unexpected:
                print(f"Unexpected credential candidate: {item['RuleID']} {item['File']}:{item['StartLine']}")
            raise ValueError(f'{len(unexpected)} credential candidates require review')
        print(f'Secret scan passed: {len(findings)} exact known upstream example contexts; no new candidates.')
    if built:
        dist = root / 'internal/web/dist'
        if not (dist / 'index.html').is_file() or not (dist / 'login.html').is_file():
            raise ValueError('Compiled panel/login pages are missing')
        for file in dist.rglob('*.js'):
            text = file.read_text(encoding='utf-8')
            if re.search(r'(?:sponsors|donate)\.sanaei\.dev', text) or re.search(r'[\'"]/sponsors(?:/logo)?[\'"]', text):
                raise ValueError('Advertising request remains in compiled JavaScript: ' + file.name)
        spec = json.loads((dist / 'openapi.json').read_text())
        if '/sponsors' in spec.get('paths', {}):
            raise ValueError('Sponsor endpoint remains in compiled API documentation')
        print('Compiled panel and login pages passed advertising checks.')
    print('No-ads source and update-source checks passed.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--report', type=Path)
    parser.add_argument('--built', action='store_true')
    parser.add_argument('--control', type=Path)
    parser.add_argument('--maintenance', action='store_true',
                        help='Self-check of the maintenance repo: provenance may still name the last published release')
    args = parser.parse_args()
    check(args.root, args.report, args.built, args.control, args.maintenance)
