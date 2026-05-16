import json
import paho.mqtt.client as mqtt

BROKER = "broker.hivemq.com"
TOPIC = "energy_venus/team28/test"

def on_message(client, userdata, msg):
    payload = msg.payload.decode()

    try:
        data = json.loads(payload)
        print("Received message:")
        print("Robot:", data.get("robot_id"))
        print("Type:", data.get("type"))
        print("Data:", data)
        print("-" * 40)
    except json.JSONDecodeError:
        print("Invalid JSON received:", payload)

client = mqtt.Client()
client.on_message = on_message

client.connect(BROKER, 1883, 60)
client.subscribe(TOPIC)

print("Listening for MQTT messages...")
client.loop_forever()