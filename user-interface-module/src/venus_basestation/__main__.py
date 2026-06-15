from __future__ import annotations

import argparse
import os
from pathlib import Path
import threading

from .dashboard import MatplotlibDashboard
from .env_config import has_mqtt_credentials, load_dotenv, resolve_source
from .fake_messages import simulated_messages
from .io_utils import iter_jsonl_messages, write_state_summary
from .map_state import MapState
from .message_schema import parse_observation
from .mqtt_client import (
    MqttCommandSender,
    MqttSubscriber,
    build_command,
    describe_mqtt_config,
    mqtt_config_from_env,
)
from .tk_dashboard import TkDashboard
from .svg_snapshot import write_svg_snapshot


def main() -> None:
    # Read a local .env (copied from .env.example) so credentials live in one
    # file. Shell exports still win — load_dotenv never overrides them.
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Venus base-station dashboard. With no --source it connects to the robot "
        "when MQTT credentials are configured, otherwise it shows simulated demo data.",
    )
    parser.add_argument(
        "--source",
        choices=["simulated", "mqtt", "jsonl"],
        default=None,
        help="Data source. Default: mqtt when credentials are set, else simulated.",
    )
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
        "--send-command",
        choices=["start", "idle", "stop"],
        help="Publish one robot command to the command topic and exit (requires --source mqtt).",
    )
    parser.add_argument(
        "--command-topic",
        help="Override the robot command topic (default: derived /pynqbridge/<username>/recv).",
    )
    parser.add_argument(
        "--mqtt-timeout",
        type=float,
        default=10.0,
        help="Seconds to wait when --mqtt-check or --send-command is used.",
    )
    parser.add_argument(
        "--mqtt-min-messages",
        type=int,
        default=1,
        help="Minimum messages to wait for when --mqtt-check is used.",
    )
    args = parser.parse_args()

    # Resolve the source: explicit --source wins; otherwise pick mqtt when
    # credentials are configured, else simulated. Print which and why.
    args.source, source_hint = resolve_source(args.source, has_credentials=has_mqtt_credentials())
    if source_hint:
        print(source_hint)

    if args.send_command and args.source != "mqtt":
        raise SystemExit("--send-command requires --source mqtt (set credentials or pass --source mqtt)")
    if args.send_command and (args.save_state or args.save_figure):
        raise SystemExit(
            "--send-command publishes one command and exits without processing telemetry; "
            "--save-state/--save-figure are not supported with it"
        )

    state = MapState()
    figure_path = Path(args.save_figure) if args.save_figure else None
    wants_svg_only = figure_path is not None and figure_path.suffix.lower() == ".svg"
    needs_dashboard = (
        not args.send_command
        and ((not args.headless and args.ui in {"tk", "matplotlib"}) or (figure_path is not None and not wants_svg_only))
    )
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

    if args.send_command:
        _run_send_command(args, config)
        return

    topics = config["topics"]
    if not topics:
        raise SystemExit("VENUS_MQTT_TOPICS must be set for --source mqtt")

    if args.mqtt_check:
        _run_mqtt_check(args, config, state, dashboard)
        return

    if isinstance(dashboard, TkDashboard):
        _run_mqtt_tk(args, config, state, dashboard)
        return

    if dashboard is not None:
        # Tk already returned above, so a remaining dashboard is matplotlib.
        # Live MQTT + matplotlib is a degraded path: run_forever() monopolizes
        # the main thread and the figure never updates interactively. Steer to
        # the Tk UI (the default and the verified live path) or headless output.
        raise SystemExit(
            "live MQTT with --ui matplotlib is not supported (the figure does not update from the "
            "network loop). Use --ui tk (default) for the live dashboard, or --headless with "
            "--save-state / --save-figure / --mqtt-check for matplotlib/SVG output."
        )

    subscriber = _build_subscriber(config, on_observation=state.apply)
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


def _run_send_command(args, config: dict) -> None:
    """One-shot robot command publish (e.g. demo-prep start/idle/stop)."""
    topic = (args.command_topic or str(config.get("command_topic") or "")).strip()
    if not topic:
        raise SystemExit("command topic is not configured; set VENUS_MQTT_COMMAND_TOPIC or pass --command-topic")
    payload = build_command(args.send_command)
    sender = MqttCommandSender(
        host=str(config["host"]),
        port=int(config["port"]),
        username=str(config["username"]),
        password=str(config["password"]),
    )
    try:
        sender.send(topic, payload, timeout=args.mqtt_timeout)
    except OSError as exc:
        raise SystemExit(
            f"MQTT command could not be sent to {config['host']}:{config['port']}: {exc}. "
            "Check TU/e network/VPN, broker availability, host, port, username, and password."
        ) from exc
    # The broker PUBACK proves only that the broker accepted the publish, not
    # that the robot received it — be explicit so an undelivered command is
    # never read as success.
    print(f"command '{args.send_command}' queued at broker for {topic} (broker accepted; robot receipt unconfirmed)")


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

    command_topic = (args.command_topic or str(config.get("command_topic") or "")).strip()
    if command_topic:
        def send_command(command: str) -> str:
            payload = build_command(command)
            if not subscriber.publish_command(command_topic, payload):
                raise RuntimeError(subscriber.last_error or "uplink not connected to broker yet")
            return command_topic

        dashboard.set_command_handler(send_command)

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
