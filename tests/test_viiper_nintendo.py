from __future__ import annotations

import struct

import pytest

from ns2pro_bridge.haptics import encode_hd_rumble2_frame
from ns2pro_bridge.protocol import ControllerState
from ns2pro_bridge.viiper_nintendo import (
    NINTENDO_BUTTONS,
    ViiperNintendoPad,
    controller_state_to_viiper,
    remap_nintendo_specials,
    viiper_feedback_to_ble,
)
from ns2pro_bridge.special_buttons import SpecialButtonRouter


def test_nintendo_wire_preserves_special_buttons_and_raw_sticks() -> None:
    state = ControllerState(
        frozenset({"a", "capture", "c", "gl", "gr", "zl"}),
        0,
        0,
        0,
        0,
        100,
        200,
        3000,
        4000,
    )
    packet = controller_state_to_viiper(state, 0x12345678)
    assert len(packet) == 28
    unpacked = struct.unpack("<IHHHHhhhhhhI", packet)
    expected_buttons = (
        NINTENDO_BUTTONS["a"]
        | NINTENDO_BUTTONS["capture"]
        | NINTENDO_BUTTONS["c"]
        | NINTENDO_BUTTONS["gl"]
        | NINTENDO_BUTTONS["gr"]
        | NINTENDO_BUTTONS["zl"]
    )
    assert unpacked[:5] == (expected_buttons, 100, 200, 3000, 4000)
    assert unpacked[5:11] == (0, 0, 0, 0, 0, 0)
    assert unpacked[11] == 0x12345678


def test_nintendo_special_mapping_replaces_physical_buttons_only() -> None:
    state = ControllerState(
        frozenset({"a", "capture", "c", "gl", "gr"}),
        10,
        20,
        30,
        40,
        100,
        200,
        300,
        400,
    )
    sent: list[tuple[int, ...]] = []
    router = SpecialButtonRouter(
        {
            "capture": "native_c",
            "c": "key_f12",
            "gl": "native_same",
            "gr": "disabled",
        },
        sent.append,
    )

    mapped = remap_nintendo_specials(state, router)

    assert mapped.pressed == frozenset({"a", "c", "gl"})
    assert mapped.raw_left_x == 100
    assert mapped.raw_right_y == 400
    assert len(sent) == 1


def test_viiper_pad_applies_native_special_mapping_before_send() -> None:
    class RecordingStream:
        def __init__(self) -> None:
            self.payloads: list[bytes] = []

        def sendall(self, payload: bytes) -> None:
            self.payloads.append(payload)

    stream = RecordingStream()
    pad = ViiperNintendoPad(
        special_mappings={
            "capture": "native_c",
            "c": "disabled",
            "gl": "native_same",
            "gr": "xinput_guide",
        }
    )
    pad._stream = stream
    state = ControllerState(
        frozenset({"capture", "c", "gl", "gr"}), 0, 0, 0, 0
    )

    pad.update(state)
    pad._stream = None

    buttons = struct.unpack("<I", stream.payloads[0][:4])[0]
    assert buttons == (
        NINTENDO_BUTTONS["c"]
        | NINTENDO_BUTTONS["gl"]
        | NINTENDO_BUTTONS["home"]
    )


def test_native_feedback_preserves_both_sixteen_byte_rumble_sides() -> None:
    # VIIPER exposes the USB HID side encoding. Use known frames with the
    # 16-bit HID amplitude at its documented 29000 reference maximum.
    def hid_frame(high_freq: int, high_amp: int, low_freq: int, low_amp: int) -> bytes:
        return bytes(
            (
                high_freq & 0xFF,
                ((high_freq >> 8) & 0x03) | ((high_amp >> 4) & 0xFC),
                ((high_amp >> 12) & 0x0F) | ((low_freq & 0x0F) << 4),
                ((low_freq >> 4) & 0x3F) | (low_amp & 0xC0),
                (low_amp >> 8) & 0xFF,
            )
        )

    left = bytes((0x50,)) + hid_frame(0x160, 29000, 0x0B8, 29000) + bytes(10)
    right = bytes((0x50,)) + hid_frame(0x120, 0, 0x0A0, 0) + bytes(10)
    feedback = left + right + bytes((0x01, 0x04))
    packet = viiper_feedback_to_ble(feedback, 3)
    assert packet is not None
    assert len(packet) == 33
    assert packet[0] == 0
    assert packet[1] == packet[17] == 0x53
    assert packet[2:7] == encode_hd_rumble2_frame(0x0B8, 1023, 0x160, 1023)
    assert packet[18:23] == encode_hd_rumble2_frame(0x0A0, 0, 0x120, 0)


def test_led_only_feedback_does_not_generate_rumble_packet() -> None:
    assert viiper_feedback_to_ble(bytes(32) + bytes((0x02, 0x01))) is None


def test_invalid_feedback_size_is_rejected() -> None:
    with pytest.raises(ValueError, match="34 bytes"):
        viiper_feedback_to_ble(bytes(33))
