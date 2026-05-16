import json
import os
import paho.mqtt.client as mqtt

BROKER = "mqtt.ics.ele.tue.nl"
TOPIC = "/pynqbridge/robot_43_1/send"

USER = "robot_43_1"
PASSWORD = os.environ.get("VENUS_MQTT_PASSWORD", "")

if not PASSWORD:
    raise RuntimeError("Set VENUS_MQTT_PASSWORD before connecting to the course MQTT broker.")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()

    try:
        data = json.loads(payload)
        print("Received message:")
        print("Topic:", msg.topic)
        print("Robot:", data.get("robot_id"))
        print("Type:", data.get("type"))
        print("Data:", data)
        print("-" * 40)
    except json.JSONDecodeError:
        print("Invalid JSON received:", payload)

client = mqtt.Client()
client.username_pw_set(USER, PASSWORD)
client.on_message = on_message

client.connect(BROKER, 1883, 60)
client.subscribe(TOPIC)

print("Listening on TU/e MQTT broker...")
client.loop_forever()
