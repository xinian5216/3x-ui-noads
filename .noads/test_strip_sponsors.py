import copy
import unittest

from strip_sponsors import replace, strip_json, strip_palette, strip_sidebar


class SponsorTransformTests(unittest.TestCase):
    def test_sidebar_supports_both_original_and_upstream_removed_ad_slots(self):
        shared = """  CrownOutlined,
  HeartOutlined,
const DONATE_URL = 'https://donate.sanaei.dev/';
  | 'sponsors'
  sponsors: CrownOutlined,
function DonateButton({ ariaLabel }: { ariaLabel: string }) {
  return <a href={DONATE_URL}><HeartOutlined /></a>;
}

function DocsButton() { return <a href="https://docs.sanaei.dev/">Docs</a>; }
      { key: '/sponsors', icon: 'sponsors', title: t('menu.sponsors') },
               <DonateButton ariaLabel={t('menu.donate') || 'Donate'} />
             <DonateButton ariaLabel={t('menu.donate') || 'Donate'} />
"""
        for slots in ("", "import SponsorSlot from '@/components/sponsor/SponsorSlot';\n  <SponsorSlot slot=\"sidebar\" />\n  <SponsorSlot slot=\"sidebar\" />\n"):
            cleaned = strip_sidebar(slots + shared)
            self.assertNotIn('Sponsor', cleaned)
            self.assertNotIn('Donate', cleaned)
            self.assertIn('https://docs.sanaei.dev/', cleaned)

    def test_sidebar_supports_panel_routes_refactor_shape(self):
        # v3.11.0 builds the nav from PANEL_ROUTES; only the donate chip remains.
        sidebar = """import { PANEL_ROUTES } from '@/routes/panelRoutes';
  HeartOutlined,
const DONATE_URL = 'https://donate.sanaei.dev/';
function DonateButton({ ariaLabel }: { ariaLabel: string }) {
  return <a href={DONATE_URL}><HeartOutlined /></a>;
}

function DocsButton() { return <a href="https://docs.sanaei.dev/">Docs</a>; }
               <DonateButton ariaLabel={t('menu.donate') || 'Donate'} />
             <DonateButton ariaLabel={t('menu.donate') || 'Donate'} />
"""
        cleaned = strip_sidebar(sidebar)
        self.assertNotIn('Donate', cleaned)
        self.assertNotIn('DONATE_URL', cleaned)
        self.assertIn('https://docs.sanaei.dev/', cleaned)

    def test_translation_updates_preserve_new_protocol_and_user_ad_tag_settings(self):
        original = {
            'menu': {'sponsors': 'Sponsors', 'donate': 'Donate', 'hosts': 'Hosts'},
            'pages': {'sponsors': {'newPlacement': 'Changed ad'}, 'inbounds': {
                'mtgPendingHandshakesMaxPerIp': 'New upstream setting', 'mtgAdTagInvalid': 'Protocol validation'}},
        }
        expected = copy.deepcopy(original)
        del expected['menu']['sponsors']
        del expected['menu']['donate']
        del expected['pages']['sponsors']
        self.assertEqual(strip_json(original, 'translation'), expected)

    def test_openapi_keeps_unrelated_protocol_schemas_and_endpoints(self):
        data = {'paths': {'/sponsors': {}, '/inbounds': {'get': {}}},
                'components': {'schemas': {'panel.SponsorList': {}, 'panel.Sponsor': {}, 'MTProto': {'adTag': {}}}}}
        self.assertEqual(strip_json(data, 'openapi'), {
            'paths': {'/inbounds': {'get': {}}}, 'components': {'schemas': {'MTProto': {'adTag': {}}}}})

    def test_command_palette_keeps_neighboring_keywords(self):
        # v3.11.0 derives palette pages from PANEL_ROUTES; the keyword map still lists the route.
        text = """export const PALETTE_KEYWORDS: Record<string, string[]> = {
  '/inbounds': ['inbounds'],
  '/sponsors': ['sponsors', 'sponsor', 'partners'],
  '/settings': ['settings', 'config'],
};
"""
        self.assertEqual(strip_palette(text), """export const PALETTE_KEYWORDS: Record<string, string[]> = {
  '/inbounds': ['inbounds'],
  '/settings': ['settings', 'config'],
};
""")

    def test_command_palette_still_strips_an_inline_sponsor_page(self):
        text = """  CrownOutlined,
const pages = [
      {
        path: '/sponsors',
        title: t('menu.sponsors'),
        icon: <CrownOutlined />,
      },
      { path: '/inbounds' },
];
  '/sponsors': ['sponsors', 'sponsor', 'partners'],
"""
        cleaned = strip_palette(text)
        self.assertNotIn('sponsors', cleaned)
        self.assertIn("{ path: '/inbounds' },", cleaned)

    def test_unknown_shared_code_structure_stops_instead_of_deleting_more(self):
        with self.assertRaises(ValueError):
            strip_palette("const newLayout = { path: '/sponsors' };\n")
        with self.assertRaises(ValueError):
            replace('one one', 'one')


if __name__ == '__main__':
    unittest.main()
