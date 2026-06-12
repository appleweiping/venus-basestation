from __future__ import annotations

import argparse
from pathlib import Path
import threading

from .dashboard import MatplotlibDashboard
from .fake_messages import simulated_messages
from .io_utils import iter_jsonl_messages, write_state_summary
from .map_state import MapState
from .message_schema import parse_observation
from .mqtt_client import MqttSubscriber, describe_mqtt_config, mqtt_config_from_env
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
    parser.add_argument(
        "--theme",
        choices=["dark", "light"],
        default="dark",
        help="Visual theme for the Tk dashboard and SVG snapshots.",
    )
    parser.add_argument("--steps", type=int, default=40, help="Number of simulated steps to run.")
    parser.add_argument("--delay", type=float, default=0.05, help="Delay between simulated steps.")
    parser.add_argument("--jsonl-path", help="Replay a JSONL file when using --source jsonl.")
    parser.add_argument("--save-figure", help="Write the final dashboard figure to this PNG path.")
    parser.add_argument("--save-state", help="Write the final map state to this JSON path.")
    parser.add_argument(
        "--mqtt-check",
        action="store_true",
        help="Print sanitized MQTT config, connect briefly, then exit.",
    )
    parser.add_argument(
        "--mqtt-timeout",
        type=float,
        default=10.0,
        help="Seconds to wait when --mqtt-check is used.",
    )
    parser.add_argument(
        "--mqtt-min-messages",
        type=int,
        default=1,
        help="Minimum messages to wait for when --mqtt-check is used.",
    )
    args = parser.parse_args()

    state = MapState()
    figure_path = Path(args.save_figure) if args.save_figure else None
    wants_svg_only = figure_path is not None and figure_path.suffix.lower() == ".svg"
    needs_dashboard = (not args.headless and args.ui in {"tk", "matplotlib"}) or (figure_path is not None and not wants_svg_only)
    dashboard = _build_dashboard(
        args.ui,
        needs_dashboard,
        allow_matplotlib_export=figure_path is not None and not wants_svg_only,
        theme=args.theme,
    )

    def handle(payload: str | bytes) -> None:
        observation = parse_observation(payload)
        state.apply(observation)
        if dashboard:
            dashboard.draw(state)

    if args.source == "simulated":
        for payload in simulated_messages(args.steps, args.delay):
            handle(payload)
        _finish(state, dashboard, args.save_figure, args.save_state, show=not args.headless, theme=args.theme)
        return

    if args.source == "jsonl":
        if not args.jsonl_path:
            raise SystemExit("--jsonl-path is required for --source jsonl")
        for payload in iter_jsonl_messages(Path(args.jsonl_path)):
            handle(payload)
        _finish(state, dashboard, args.save_figure, args.save_state, show=not args.headless, theme=args.theme)
        return

    config = mqtt_config_from_env()
    print(describe_mqtt_config(config))
    topics = config["topics"]
    if not topics:
        raise SystemExit("VENUS_MQTT_TOPICS must be set for --source mqtt")

    if args.mqtt_check:
        _run_mqtt_check(args, config, state, dashboard)
        return

    if isinstance(dashboard, TkDashboard):
        _run_mqtt_tk(args, config, state, dashboard)
        return

    subscriber = _build_subscriber(config, on_observation=lambda observation: (state.apply(observation), dashboard and dashboard.draw(state)))
    try:
        subscriber.run_forever()
    except OSError as exc:
        raise SystemExit(
            f"MQTT could not connect to {config['host']}:{config['port']}: {exc}. "
            "Check TU/e network/VPN, broker availability, host, port, username, and password."
        ) from exc


def _build_subscriber(config: dict, **kwargs) -> MqttSubscriber:
    return MqttSubscriber(
        host=str(config["host"]),
        port=int(config["port"]),
        username=str(config["username"]),
        password=str(config["password"]),
        topics=list(config["topics"]),
        **kwargs,
    )


def _run_mqtt_check(args, config: dict, state: MapState, dashboard) -> None:
    subscriber = _build_subscriber(
        config,
        on_observation=lambda observation: (state.apply(observation), dashboard and dashboard.draw(state)),
    )
    try:
        count = subscriber.run_until(args.mqtt_timeout, min_messages=args.mqtt_min_messages)
    except OSError as exc:
        raise SystemExit(
            f"MQTT check could not connect to {config['host']}:{config['port']}: {exc}. "
            "Check TU/e network/VPN, broker availability, host, port, username, and password."
        ) from exc
    if subscriber.connection_error:
        _finish(state, dashboard, args.save_figure, args.save_state, show=False, theme=args.theme)
        raise SystemExit(subscriber.connection_error)
    if subscriber.subscription_errors:
        _finish(state, dashboard, args.save_figure, args.save_state, show=False, theme=args.theme)
        raise SystemExit("; ".join(subscriber.subscription_errors))
    if count < args.mqtt_min_messages:
        _finish(state, dashboard, args.save_figure, args.save_state, show=False, theme=args.theme)
        raise SystemExit(
            f"MQTT check received {count} messages in {args.mqtt_timeout:g}s; "
            "connection may be OK but topic/payload/live robot traffic still needs checking."
        )
    _finish(state, dashboard, args.save_figure, args.save_state, show=False, theme=args.theme)


def _run_mqtt_tk(args, config: dict, state: MapState, dashboard: TkDashboard) -> None:
    """Live MQTT with the Tk dashboard.

    The paho network loop runs on a daemon thread and only enqueues events;
    the Tk thread drains the queue, so no widget is ever touched off-thread.
    """
    subscriber = _build_subscriber(
        config,
        on_observation=lambda observation: dashboard.submit("obs", observation),
        on_log=lambda message: (print(message), dashboard.submit("log", message)),
        on_connect_change=lambda ok, broker: dashboard.submit("conn", (ok, broker)),
    )

    def run_subscriber() -> None:
        try:
            subscriber.run_forever()
        except OSError as exc:
            message = (
                f"MQTT could not connect to {config['host']}:{config['port']}: {exc}. "
                "Check TU/e network/VPN, broker availability, host, port, username, and password."
            )
            print(message)
            dashboard.submit("log", message)
            dashboard.submit("conn", (False, ""))

    thread = threading.Thread(target=run_subscriber, name="mqtt-subscriber", daemon=True)
    thread.start()
    dashboard.start_pump(state)
    dashboard.show()
    _finish(state, None, args.save_figure, args.save_state, show=False, theme=args.theme)


def _finish(state: MapState, dashboard, save_figure: str | None, save_state: str | None, *, show: bool, theme: str = "dark") -> None:
    print(f"processed {state.messages_seen} messages")
    if save_state:
        path = write_state_summary(save_state, state)
        print(f"wrote state summary to {path}")
    if dashboard and save_figure:
        if Path(save_figure).suffix.lower() == ".svg":
            path = write_svg_snapshot(save_figure, state, theme=theme)
            print(f"wrote svg snapshot to {path}")
        else:
            dashboard.save(save_figure)
            print(f"wrote figure to {save_figure}")
    elif save_figure:
        if Path(save_figure).suffix.lower() != ".svg":
            raise SystemExit("PNG export requires matplotlib. Install dashboard extras or save to an .svg path instead.")
        path = write_svg_snapshot(save_figure, state, theme=theme)
        print(f"wrote svg snapshot to {path}")
    if dashboard and show:
        dashboard.show()


def _build_dashboard(ui: str, needs_dashboard: bool, *, allow_matplotlib_export: bool, theme: str = "dark"):
    if not needs_dashboard:
        return None
    if ui == "tk" and not allow_matplotlib_export:
        return TkDashboard(theme=theme)
    return MatplotlibDashboard()


if __name__ == "__main__":
    main()
