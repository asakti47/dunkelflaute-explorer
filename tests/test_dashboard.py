"""Regression checks for synchronized dashboard controls and event inspection.

Run directly with the project interpreter; no additional test dependency needed.
"""
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


class DashboardTest(unittest.TestCase):
    def test_load_failure_and_retry(self):
        path = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")
        script = f"""
import runpy
import streamlit as st
from unittest.mock import patch
st.cache_resource.clear()
st.cache_data.clear()
if not st.session_state.get('data_retried', False):
    st.session_state.data_retried = True
    with patch('dfx.panel.Panel.load', side_effect=OSError('Controlled read failure')):
        runpy.run_path({path!r}, run_name='__main__')
else:
    runpy.run_path({path!r}, run_name='__main__')
"""
        app = AppTest.from_string(script, default_timeout=600).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Couldn't load weather data" in error.value for error in app.error))
        app.button[-1].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["thr"], 10)
        self.assertEqual(len(app.get("plotly_chart")), 5)

    def test_empty_events(self):
        path = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")
        script = f"""
import runpy
import streamlit as st
from unittest.mock import patch
from dfx import events
st.cache_data.clear()
original_run = events.run
def empty_event_list(cf, definition):
    ev, metrics, cutoff = original_run(cf, definition)
    return ev.iloc[:0], metrics, cutoff
with patch('dfx.events.run', side_effect=empty_event_list):
    runpy.run_path({path!r}, run_name='__main__')
"""
        app = AppTest.from_string(script, default_timeout=600).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("No events match" in item.value for item in app.info))
        self.assertFalse(any(box.key == "event_date" for box in app.selectbox))

    def test_controls_event_selection_and_reset(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py"),
                                default_timeout=600).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Dunkelflaute Explorer")
        self.assertEqual([tab.label for tab in app.tabs], ["Overview", "Events", "Method & data"])
        self.assertEqual(app.tabs[0].subheader[0].value, "No clear trend in winter low-output days")
        headline = app.get("html")[0].proto.body
        for text in ["Dunkelflaute frequency", "Dunkelflaute event length", "Not significant", "p =",
                     "Locations with a significant trend", "Weather-driver effects (significant)",
                     'id="dfx-rising-tooltip"', 'id="dfx-falling-tooltip"']:
            self.assertIn(text, headline)
        self.assertEqual(app.sidebar.button[0].label, "Reset")
        settings = next(item for item in app.sidebar.expander if item.label == "Model settings")
        self.assertFalse(settings.proto.expanded)
        self.assertEqual({item.key for item in settings.slider}, {"thr", "mix"})
        self.assertEqual({item.key for item in settings.toggle}, {"remove_wind", "remove_ghi"})
        more = next(item for item in app.tabs[0].expander if item.label == "More analysis")
        self.assertFalse(more.proto.expanded)
        self.assertEqual(len(more.get("plotly_chart")), 2)
        self.assertEqual(app.tabs[1].selectbox[0].key, "event_date")
        self.assertEqual(app.session_state["event_date"], "2024-11-04")
        self.assertGreater(len(app.selectbox(key="event_date").options), 25)

        # Selecting an event survives unrelated weather comparison changes.
        event = app.selectbox(key="event_date").options[1].split(" — ")[0]
        app.selectbox(key="event_date").set_value(event).run()
        app.toggle(key="remove_wind").set_value(True).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["event_date"], event)

        app.slider(key="thr").set_value(15).run()
        self.assertFalse(app.exception)
        if app.session_state["event_date"] != event:
            self.assertTrue(any("previous event" in item.value for item in app.info))
        app.radio(key="min_days").set_value(3).run()
        app.slider(key="mix").set_value(0.6).run()
        app.selectbox(key="turbine").set_value("older").run()
        app.selectbox(key="metric").set_value("count").run()
        app.toggle(key="remove_ghi").set_value(True).run()
        self.assertFalse(app.exception)

        app.button[0].click().run()
        self.assertFalse(app.exception)
        for key, value in dict(thr=10, min_days=2, mix=0.5, turbine="default",
                               metric="total_days", season="winter",
                               remove_wind=False, remove_ghi=False).items():
            self.assertEqual(app.session_state[key], value, key)
        self.assertEqual(app.session_state["event_date"], "2024-11-04")
        self.assertTrue(any("10th percentile" in item.value for item in app.tabs[1].caption))
        self.assertEqual(len(app.get("plotly_chart")), 5)
        table = next(frame.value for frame in app.dataframe if "Modeled CF (%)" in frame.value)
        self.assertEqual(int(table["Selected event"].sum()), 10)
        self.assertTrue((table.loc[table["Selected event"], "Modeled CF (%)"] <
                         table.loc[table["Selected event"], "Cutoff (%)"]).all())


if __name__ == "__main__":
    unittest.main()
