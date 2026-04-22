from __future__ import annotations

import argparse

from .dashboard import MatplotlibDashboard
from .fake_messages import simulated_messages
from .map_state import MapState
from .message_schema import parse_observation
from .mqtt_client import MqttSubscriber, mqtt_config_from_env


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["simulated", "mqtt"], default="simulated")
    parser.add_argument("--headless", action="store_true", help="Process data without opening a dashboard window.")
    parser.add_argument("--steps", type=int, default=40, help="Number of simulated steps to run.")
    parser.add_argument("--delay", type=float, default=0.05, help="Delay between simulated steps.")
    args = parser.parse_args()

    state = MapState()
    dashboard = None if args.headless else MatplotlibDashboard()

    def handle(payload: str | bytes) -> None:
        observation = parse_observation(payload)
        state.apply(observation)
        if dashboard:
            dashboard.draw(state)

    if args.source == "simulated":
        for payload in simulated_messages(args.steps, args.delay):
            handle(payload)
        print(f"processed {state.messages_seen} messages")
        if dashboard:
            dashboard.show()
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


if __name__ == "__main__":
    main()

