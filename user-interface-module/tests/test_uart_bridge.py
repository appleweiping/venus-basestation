"""Offline tests for the UART->MQTT bridge frame parser.

The bridge (tools/uart_mqtt_bridge.py) is a standalone single file meant to be
copied onto the PYNQ, so it is loaded here by path rather than imported as a
package module. Only the pure frame-parsing logic is tested — the serial and
MQTT I/O require hardware and a broker.
"""

import importlib.util
from pathlib import Path

_BRIDGE_PATH = Path(__file__).resolve().parent.parent / "tools" / "uart_mqtt_bridge.py"
_spec = importlib.util.spec_from_file_location("uart_mqtt_bridge", _BRIDGE_PATH)
uart_mqtt_bridge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(uart_mqtt_bridge)

parse_frames = uart_mqtt_bridge.parse_frames
resolve_topic = uart_mqtt_bridge.resolve_topic


def frame(payload: bytes) -> bytes:
    """Build a frame exactly like the firmware's send_message_uart()."""
    return len(payload).to_bytes(4, "little") + payload


POS = b'{"robot_id":"A","type":"position_update","x":12.34,"y":56.78,"heading":90.00}'
BLOCK = b'{"robot_id":"A","type":"block_found","x":2.34,"y":5.67,"color":"Red","size":1}'


def test_single_complete_frame() -> None:
    payloads, remaining = parse_frames(frame(POS))
    assert payloads == [POS]
    assert remaining == b""


def test_two_back_to_back_frames() -> None:
    payloads, remaining = parse_frames(frame(POS) + frame(BLOCK))
    assert payloads == [POS, BLOCK]
    assert remaining == b""


def test_incomplete_frame_is_buffered() -> None:
    data = frame(POS)
    head, tail = data[:20], data[20:]

    payloads, remaining = parse_frames(head)
    assert payloads == []
    assert remaining == head  # nothing emitted, all kept

    payloads, remaining = parse_frames(remaining + tail)
    assert payloads == [POS]
    assert remaining == b""


def test_frame_split_across_reads_reassembles() -> None:
    data = frame(POS) + frame(BLOCK)
    buffer = b""
    out: list[bytes] = []
    for i in range(0, len(data), 7):  # arbitrary small chunks
        buffer += data[i : i + 7]
        payloads, buffer = parse_frames(buffer)
        out.extend(payloads)
    assert out == [POS, BLOCK]
    assert buffer == b""


def test_desync_garbage_prefix_recovers() -> None:
    # Random leading bytes (as if the bridge connected mid-stream) then a frame.
    noise = b"\x99\x01\x7f\xab\x00"
    payloads, remaining = parse_frames(noise + frame(POS))
    assert payloads == [POS]
    assert remaining == b""


def test_non_json_payload_is_rejected() -> None:
    # A plausible length but the payload is not a JSON object -> treated as
    # desync and skipped, not forwarded.
    bogus = (5).to_bytes(4, "little") + b"hello"
    payloads, remaining = parse_frames(bogus)
    assert payloads == []


def test_oversized_length_is_rejected() -> None:
    huge = (10 ** 9).to_bytes(4, "little") + b"{}"
    payloads, _ = parse_frames(huge, max_payload=8192)
    assert payloads == []


def test_resolve_topic_prefers_explicit_then_username() -> None:
    assert resolve_topic("/custom/send", "robot_43_1") == "/custom/send"
    assert resolve_topic(None, "robot_43_1") == "/pynqbridge/43/send"
