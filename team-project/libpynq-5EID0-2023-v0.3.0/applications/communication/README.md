# UART Test

This module documents the PYNQ-side UART communication functions found in `communication.c` and the expected payload structure for the receiving system.

## Message framing

Each UART message is sent as:

1. 4-byte payload length
2. Payload bytes

The payload is a JSON string. The length is the number of bytes in the JSON payload and must be read before the JSON data itself.

## Common payload fields

All messages contain:

- `robot_id`: always `"A"`
- `type`: the payload category
- `x`, `y`: floating-point coordinates with exactly two decimal places

## JSON functions

### `send_position_update(float x, float y, float angle)`

Sends the robot position and heading.

Payload example:

```json
{
  "robot_id":"A",
  "type":"position_update",
  "x":12.34,
  "y":56.78,
  "heading":90.00
}
```

### `send_block_found(float x, float y, char *color, int size)`

Sends a block detection event.

Fields:

- `x`, `y`: block position
- `color`: block color string
- `size`: block size identifier

Payload example:

```json
{
  "robot_id":"A",
  "type":"block_found",
  "x":12.34,
  "y":56.78,
  "color":"red",
  "size":1
}
```

### `send_border_found(float x, float y)`

Sends a border detection event.

Payload example:

```json
{
  "robot_id":"A",
  "type":"border_found",
  "x":12.34,
  "y":56.78
}
```

### `send_mountain_found(float x, float y)`

Sends a mountain detection event.

Payload example:

```json
{
  "robot_id":"A",
  "type":"mountain_found",
  "x":12.34,
  "y":56.78
}
```

### `send_cliff_found(float x, float y)`

Sends a cliff detection event.

Payload example:

```json
{
  "robot_id":"A",
  "type":"cliff_found",
  "x":12.34,
  "y":56.78
}
```

## Receiver responsibilities

The receiving side must:

- read the 4-byte length prefix
- read exactly that many bytes of JSON
- parse the JSON payload
- handle `type` dispatch for the different event messages

The coordinate and heading values are formatted as two-decimal floats, so the receiver should parse them as floating-point numbers.
