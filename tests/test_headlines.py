"""Check separate location hover lists and zero-count/escaping behavior."""
import unittest

import pandas as pd

from dfx.headlines import headline_html


class HeadlineTest(unittest.TestCase):
    def test_location_lists_match_corrected_significance_and_direction(self):
        cells = pd.DataFrame([
            dict(lat=51.5, lon=7, slope_decade=1.2, significant_fdr=True),
            dict(lat=52.5, lon=13, slope_decade=-.8, significant_fdr=True),
            dict(lat=53.5, lon=10, slope_decade=3, significant_fdr=False),
        ])
        trend = dict(slope_decade=0, significant=False, p_mk_mod=.9)
        html = headline_html(trend, trend, cells, [], "days", "test <measure>")
        rising = html.split('id="dfx-rising-tooltip">')[1].split('</span>')[0]
        falling = html.split('id="dfx-falling-tooltip">')[1].split('</span>')[0]
        self.assertIn("51.5°N, 7.0°E: +1.20 days per decade", rising)
        self.assertNotIn("52.5°N", rising)
        self.assertIn("52.5°N, 13.0°E: -0.80 days per decade", falling)
        self.assertNotIn("53.5°N", html)
        self.assertIn('>1 rising</button>', html)
        self.assertIn('>1 falling</button>', html)
        self.assertIn("test &lt;measure&gt;", html)
        self.assertEqual(html.count('<article class="dfx-card">'), 4)
        self.assertIn("None detected", html)

        cells["significant_fdr"] = False
        html = headline_html(trend, trend, cells, ["Wind +1.0"], "days", "test")
        self.assertIn('>0 rising</button>', html)
        self.assertIn('>0 falling</button>', html)
        self.assertIn("No grid locations have a significant rising trend", html)
        self.assertIn("No grid locations have a significant falling trend", html)
        self.assertIn("Wind +1.0", html)


if __name__ == "__main__":
    unittest.main()
