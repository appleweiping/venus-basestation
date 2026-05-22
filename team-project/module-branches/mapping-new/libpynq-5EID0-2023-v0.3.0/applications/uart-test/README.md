# UART Test

This test sends a JSON payload from the PYNQ to the ESP32 using the required UART format.

Format:
4 bytes payload length + payload characters

First test:
- no sensors
- fixed JSON message
- checks if PYNQ can send a correctly formatted message to ESP32

Expected result:
The ESP32 forwards the payload to MQTT, and the PC subscriber receives it.