import json
import time
import random
import paho.mqtt.client as mqtt

BROKER = "broker.hivemq.com"
TOPIC = "energy_venus/team28/test"

client = mqtt.Client()
client.connect(BROKER, 1883, 60)

x = 0
y = 0
heading = 90

while True:
    position_message = {
        "robot_id": "A",
        "type": "position_update",
        "x": x,
        "y": y,
        "heading": heading
    }

    client.publish(TOPIC, json.dumps(position_message))
    print("Sent position:", position_message)

    if random.randint(1, 4) == 1:
        distance_mm = random.randint(50, 300)

        event_message = {
            "robot_id": "A",
            "type": "rock_detected",
            "x": x,
            "y": y,
            "distance_mm": distance_mm,
            "color": "red",
            "size": "small",
            "temperature": 28.5
        }

        client.publish(TOPIC, json.dumps(event_message))
        print("Sent event:", event_message)

    x += 1
    time.sleep(1)