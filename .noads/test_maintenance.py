import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from check import check
from clean_docs import SUPPORT_HEADINGS, check_docs, clean_docs, clean_text
from preserve import DIRECTORIES, FILES, preserve_control, verify_control


class DocumentationTests(unittest.TestCase):
    def test_actual_persian_heading_is_recognized(self):
        title = '\u067e\u0634\u062a\u06cc\u0628\u0627\u0646\u06cc \u0627\u0632 \u067e\u0631\u0648\u0698\u0647'
        self.assertEqual(clean_text('## ' + title + '\nAd\n## Docs\nKeep\n'), '## Docs\nKeep\n')

    def test_translated_support_sections_preserve_following_license_and_attribution(self):
        for title in SUPPORT_HEADINGS:
            with self.subTest(title=title):
                text = '# Project\nAuthor: MHSanaei\n\n## ' + title + '\n'
                text += '<a href="https://www.buymeacoffee.com/MHSanaei">Coffee</a>\n'
                text += '### Crypto\nhttps://nowpayments.io/donation/example\n'
                suffix = '## License\nGPL-3.0\n'
                self.assertEqual(clean_text(text + suffix), '# Project\nAuthor: MHSanaei\n\n' + suffix)

    def test_new_sponsor_section_with_unknown_vendor_is_removed(self):
        text = '# App\n## Our Sponsors\n[Vendor](https://new-vendor.example)\n## Install\nInstructions\n'
        self.assertEqual(clean_text(text), '# App\n## Install\nInstructions\n')

    def test_technical_support_docs_and_fenced_heading_examples_are_preserved(self):
        text = '# Support for Linux\nDocumentation\n```md\n## Sponsors\nexample\n```\n## Credits\nMHSanaei\n'
        self.assertEqual(clean_text(text), text)

    def test_html_and_setext_sections_and_idempotency(self):
        for text in ('<h2>Sponsors</h2>\nAd\n<h2>License</h2>\nGPL\n',
                     'Donations\n---------\nAd\nLicense\n-------\nGPL\n'):
            cleaned = clean_text(text)
            self.assertNotIn('Ad\n', cleaned)
            self.assertIn('GPL\n', cleaned)
            self.assertEqual(clean_text(cleaned), cleaned)

    def test_unrecognized_inline_funding_placement_blocks_release(self):
        with self.assertRaises(ValueError):
            clean_text('# Installation\n[Special link](https://donate.sanaei.dev)\n')

    def test_nested_readmes_are_cleaned_and_both_funding_names_are_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', '-C', str(root), 'init', '-q'], check=True)
            (root / 'nested').mkdir()
            (root / '.github').mkdir()
            readme = root / 'nested/README.zh_CN.md'
            readme.write_text('# App\n## 赞助商\nBanner\n## 使用说明\nDocs\n', encoding='utf-8')
            for name in ('FUNDING.yml', 'FUNDING.yaml'):
                (root / '.github' / name).write_text('github: upstream\n')
            subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
            with self.assertRaises(ValueError):
                check_docs(root)
            clean_docs(root)
            check_docs(root)
            self.assertEqual(readme.read_text(encoding='utf-8'), '# App\n## 使用说明\nDocs\n')


class PreservationTests(unittest.TestCase):
    def test_upstream_cannot_replace_agent_rules_scripts_workflows_or_root_docs(self):
        with tempfile.TemporaryDirectory() as directory:
            control, source = Path(directory) / 'main', Path(directory) / 'upstream'
            control.mkdir()
            source.mkdir()
            for name in FILES:
                (control / name).write_text('trusted downstream ' + name)
                (source / name).write_text('upstream replacement')
            for name in DIRECTORIES:
                (control / name).mkdir(parents=True)
                (source / name).mkdir(parents=True)
                (control / name / 'trusted.py').write_text('downstream policy')
                (source / name / 'unwanted.py').write_text('upstream workflow or script')
            preserve_control(source, control)
            verify_control(source, control)
            for name in DIRECTORIES:
                self.assertFalse((source / name / 'unwanted.py').exists())
            (source / 'AGENTS.md').write_text('overwritten after restore')
            with self.assertRaises(ValueError):
                verify_control(source, control)
            preserve_control(source, control)
            (source / '.noads/trusted.py').write_text('changed after restore')
            with self.assertRaises(ValueError):
                verify_control(source, control)
            preserve_control(source, control)
            (source / '.github/workflows/unwanted.yml').write_text('new upstream workflow')
            with self.assertRaises(ValueError):
                verify_control(source, control)

    def test_missing_downstream_policy_stops_instead_of_trusting_upstream(self):
        with tempfile.TemporaryDirectory() as directory:
            control, source = Path(directory) / 'main', Path(directory) / 'upstream'
            control.mkdir()
            source.mkdir()
            (source / 'AGENTS.md').write_text('untrusted')
            with self.assertRaises(ValueError):
                preserve_control(source, control)
            self.assertEqual((source / 'AGENTS.md').read_text(encoding='utf-8'), 'untrusted')


class MaintenanceProvenanceTests(unittest.TestCase):
    """The maintenance self-check must not demand provenance of an unreleased transform."""

    def maintenance_root(self, directory):
        root = Path(directory)
        (root / '.noads').mkdir()
        (root / '.noads/strip_sponsors.py').write_text('candidate transform\n', encoding='utf-8')
        (root / '.noads/provenance.json').write_text(json.dumps({
            'upstream_tag': 'v3.10.2',
            'source_transform_sha256': hashlib.sha256(b'published transform').hexdigest(),
        }), encoding='utf-8')
        (root / 'AGENTS.md').write_text('rules\n', encoding='utf-8')
        for name in ('frontend/src/routes.tsx', 'frontend/src/layouts/AppSidebar.tsx',
                     'frontend/src/pages/index/IndexPage.tsx', 'frontend/src/pages/login/LoginPage.tsx',
                     'internal/web/controller/index.go', 'install.sh', 'update.sh', 'x-ui.sh',
                     'internal/web/service/panel/panel.go'):
            file = root / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text('package panel\n', encoding='utf-8')
        subprocess.run(['git', '-C', str(root), 'init', '-q'], check=True)
        return root

    def test_maintenance_self_check_tolerates_the_next_transform(self):
        with tempfile.TemporaryDirectory() as directory:
            check(self.maintenance_root(directory), maintenance=True)

    def test_maintenance_refuses_to_relax_a_release_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.maintenance_root(directory)
            for kwargs in ({'built': True}, {'report': Path('report.json')}, {'control': root}):
                with self.subTest(**kwargs):
                    with self.assertRaises(ValueError):
                        check(root, maintenance=True, **kwargs)

    def test_generated_tree_still_enforces_the_provenance_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                check(self.maintenance_root(directory))


if __name__ == '__main__':
    unittest.main()
