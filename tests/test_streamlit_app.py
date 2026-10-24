"""Smoke-test navigation and rendering without launching expensive jobs."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_every_application_section_renders_without_errors() -> None:
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / "app.py"), default_timeout=45).run()
    pages = ["Overview", "Monthly Planner", "Optimization Lab", "Benchmark Results", "Meal Library", "Settings", "About"]

    for page in pages:
        navigation = next(item for item in app.radio if item.label == "Navigation")
        navigation.set_value(page)
        app.run()
        assert not app.exception, f"{page} raised an application exception"
        assert app.title, f"{page} did not render its title"
