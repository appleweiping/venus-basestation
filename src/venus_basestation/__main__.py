from __future__ import annotations

import argparse
from pathlib import Path

from .dashboard import MatplotlibDashboard
from .fake_messages import simulated_messages
from .io_utils import iter_jsonl_messages, write_state_summary
from .map_state import MapState
from .message_schema import parse_observation
from .mqtt_client import MqttSubscriber, mqtt_config_from_env
from .tk_dashboard import TkDashboard
from .svg_snapshot import write_svg_snapshot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["simulated", "mqtt", "jsonl"], default="simulated")
    parser.add_argument("--headless", action="store_true", help="Process data without opening a dashboard window.")
    parser.add_argument(
        "--ui",
        choices=["tk", "matplotlib"],
        default="tk",
        help="Interactive UI to use when not running headless.",
    )
    parser.add_argument("--steps", type=int, default=40, help="Number of simulated steps to run.")
    parser.add_argument("--delay", type=float, default=0.05, help="Delay between simulated steps.")
    parser.add_argument("--jsonl-path", help="Replay a JSONL file when using --source jsonl.")
    parser.add_argument("--save-figure", help="Write the final dashboard figure to this PNG path.")
    parser.add_argument("--save-state", help="Write the final map state to this JSON path.")
    args = parser.parse_args()

    state = MapState()
    figure_path = Path(args.save_figure) if args.save_figure else None
    wants_svg_only = figure_path is not None and figure_path.suffix.lower() == ".svg"
    needs_dashboard = (not args.headless and args.ui in {"tk", "matplotlib"}) or (figure_path is not None and not wants_svg_only)
    dashboard = _build_dashboard(args.ui, needs_dashboard, allow_matplotlib_export=figure_path is not None and not wants_svg_only)

    def handle(payload: str | bytes) -> None:
        observation = parse_observation(payload)
        state.apply(observation)
        if dashboard:
            dashboard.draw(state)

    if args.source == "simulated":
        for payload in simulated_messages(args.steps, args.delay):
            handle(payload)
        _finish(state, dashboard, args.save_figure, args.save_state, show=not args.headless)
        return

    if args.source == "jsonl":
        if not args.jsonl_path:
            raise SystemExit("--jsonl-path is required for --source jsonl")
        for payload in iter_jsonl_messages(Path(args.jsonl_path)):
            handle(payload)
        _finish(state, dashboard, args.save_figure, args.save_state, show=not args.headless)
        return

    config = mqtt_config_from_env()
    topics = config["topics"]
    if not topics:
        raise SystemExit("VENUS_MQTT_TOPICS must be set for --source mqtt")

    subscriber = MqttSubscriber(
        host=str(config["host"]),
        username=str(config["username"]),
        password=str(config["password"]),
        topics=list(topics),
        on_observation=lambda observation: (state.apply(observation), dashboard and dashboard.draw(state)),
    )
    subscriber.run_forever()


def _finish(state: MapState, dashboard, save_figure: str | None, save_state: str | None, *, show: bool) -> None:
    print(f"processed {state.messages_seen} messages")
    if save_state:
        path = write_state_summary(save_state, state)
        print(f"wrote state summary to {path}")
    if dashboard and save_figure:
        if Path(save_figure).suffix.lower() == ".svg":
            path = write_svg_snapshot(save_figure, state)
            print(f"wrote svg snapshot to {path}")
        else:
            dashboard.save(save_figure)
            print(f"wrote figure to {save_figure}")
    elif save_figure:
        if Path(save_figure).suffix.lower() != ".svg":
            raise SystemExit("PNG export requires matplotlib. Install dashboard extras or save to an .svg path instead.")
        path = write_svg_snapshot(save_figure, state)
        print(f"wrote svg snapshot to {path}")
    if dashboard and show:
        dashboard.show()


def _build_dashboard(ui: str, needs_dashboard: bool, *, allow_matplotlib_export: bool):
    if not needs_dashboard:
        return None
    if ui == "tk" and not allow_matplotlib_export:
        return TkDashboard()
    return MatplotlibDashboard()


if __name__ == "__main__":
    main()
