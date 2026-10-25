"""Dashboard behaviour that needs a real Tk display or matplotlib.

Each test skips itself when its dependency is missing (for example Tk on a
CI runner without a display), so the core test suite stays dependency-free.
"""

from __future__ import annotations

from pathlib import Path
import warnings

import pytest

from venus_basestation.__main__ import main
from venus_basestation.map_state import MapState
from venus_basestation.message_schema import parse_observation

DEMO = Path(__file__).resolve().parent.parent / "examples" / "demo_mission.jsonl"


@pytest.fixture
def tk_dashboard():
    tk = pytest.importorskip("tkinter")
    from venus_basestation.tk_dashboard import TkDashboard

    try:
        dashboard = TkDashboard()
    except tk.TclError as exc:
        pytest.skip(f"no Tk display: {exc}")
    dashboard.root.withdraw()  # never show a window while testing
    yield dashboard
    if not dashboard.closed:
        dashboard.close()


def _demo_state(limit: int | None = None) -> MapState:
    state = MapState()
    lines = DEMO.read_text(encoding="utf-8").splitlines()
    for line in lines[:limit]:
        state.apply(parse_observation(line))
    return state


def test_tk_draw_after_window_destroyed_does_not_raise(tk_dashboard) -> None:
    tk_dashboard.draw(_demo_state(20))
    # What happens when the window is closed in the middle of a replay.
    tk_dashboard.root.destroy()
    tk_dashboard._last_render = 0.0
    tk_dashboard.draw(_demo_state(40))
    assert tk_dashboard.closed
    tk_dashboard.show()  # returns at once instead of raising TclError


def test_tk_close_button_stops_drawing(tk_dashboard) -> None:
    tk_dashboard.close()
    tk_dashboard.draw(_demo_state(10))
    assert tk_dashboard.closed


def test_tk_legend_canvas_fits_all_labels(tk_dashboard) -> None:
    canvas = tk_dashboard.legend_canvas
    right_edge = canvas.bbox("all")[2]
    assert int(canvas["width"]) >= right_edge


def test_tk_robot_labels_are_drawn_above_detections(tk_dashboard) -> None:
    state = MapState()
    state.apply(parse_observation({"robot_id": "robot_28_1", "event_type": "robot_position", "x": 150, "y": 77}))
    state.apply(
        parse_observation(
            {"robot_id": "robot_15_1", "event_type": "rock", "x": 152, "y": 78, "color": "red", "size": "large"}
        )
    )
    tk_dashboard.draw(state)
    tk_dashboard._render()
    top_item = tk_dashboard.canvas.find_all()[-1]
    assert "robot_label" in tk_dashboard.canvas.gettags(top_item)


def test_replay_stops_when_window_is_closed(monkeypatch, capsys) -> None:
    class ClosingDashboard:
        """Stands in for the Tk window; the user closes it after 5 messages."""

        def __init__(self) -> None:
            self.closed = False
            self.draws = 0

        def draw(self, state) -> None:
            self.draws += 1
            if self.draws == 5:
                self.closed = True

        def show(self) -> None:
            pass  # TkDashboard.show() returns at once once the window is closed

    fake = ClosingDashboard()
    monkeypatch.setattr("venus_basestation.__main__._build_dashboard", lambda *args, **kwargs: fake)
    monkeypatch.setattr("sys.argv", ["venus_basestation", "--source", "jsonl", "--jsonl-path", str(DEMO)])

    main()

    assert fake.draws == 5
    assert "processed 5 messages" in capsys.readouterr().out


def test_headless_png_export_has_no_aspect_warnings(tmp_path: Path, monkeypatch) -> None:
    pytest.importorskip("matplotlib")
    output = tmp_path / "mission.png"
    monkeypatch.setattr(
        "sys.argv",
        [
            "venus_basestation",
            "--source",
            "jsonl",
            "--jsonl-path",
            str(DEMO),
            "--headless",
            "--save-figure",
            str(output),
        ],
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        main()

    assert output.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert not [w for w in caught if "Ignoring fixed" in str(w.message)]
    assert not [w for w in caught if "non-interactive" in str(w.message)]

