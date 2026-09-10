"""Pure protocol decoding for the Switch 2 Pro Controller.

The constants and report layout are based on the MIT-licensed joycon2cpp and
Switch2BTLink projects. Keeping this module free of Bluetooth/driver imports
makes the reverse-engineered wire format independently testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

NINTENDO_MANUFACTURER_ID = 0x0553
# Byte 4 has changed between observed controller/firmware advertising formats.
# Keep the Nintendo frame prefix and product ID strict while tolerating that
# format-revision byte so regional or updated official units are not rejected.
SWITCH2_ADVERTISEMENT_PREFIX = bytes((0x01, 0x00, 0x03, 0x7E))
SWITCH2_PRO_PRODUCT_ID = 0x2069

INPUT_REPORT_UUID = "ab7de9be-89fe-49ad-828f-118f09df7fd2"
WRITE_COMMAND_UUID = "649d4ac9-8eb7-4e6c-af44-1ea54fe5f005"
ACK_REPORT_UUID = "c765a961-d9d8-4d36-a20a-5315b111836a"
PRO_RUMBLE_UUID = "cc483f51-9258-427d-a939-630c31f72b05"

# Current Pro2 BLE bring-up sequence used by XinHeLianSheng v6.2.32.  These
# are direct command-channel writes; no 33-byte rumble prefix is used.
INITIALIZATION_COMMANDS = (
    bytes.fromhex("03 91 01 0D 00 08 00 00 01 00 FF FF FF FF FF FF"),
    bytes.fromhex("07 91 01 01 00 00 00 00"),
    bytes.fromhex("16 91 01 01 00 00 00 00"),
    bytes.fromhex("15 91 01 03 00 01 00 00 00"),
    bytes.fromhex("0C 91 01 02 00 04 00 00 FF 00 00 00"),
    bytes.fromhex("11 91 01 03 00 00 00 00"),
    bytes.fromhex(
        "0A 91 01 08 00 14 00 00 01 FF FF FF FF FF FF FF FF 35 00 46 "
        "00 00 00 00 00 00 00 00"
    ),
    bytes.fromhex("0C 91 01 04 00 04 00 00 FF 00 00 00"),
    bytes.fromhex("03 91 01 0A 00 04 00 00 09 00 00 00"),
    bytes.fromhex("10 91 01 01 00 00 00 00"),
    bytes.fromhex("01 91 01 0C 00 00 00 00"),
    bytes.fromhex("01 91 01 01 00 04 00 00 00 00 00 00"),
    bytes.fromhex("09 91 01 07 00 08 00 00 01 00 00 00 00 00 00 00"),
    bytes.fromhex("02 91 01 04 00 08 00 00 09 7E 00 00 A8 30 01 00"),
    bytes.fromhex("02 91 01 04 00 08 00 00 09 7E 00 00 E8 30 01 00"),
)

BUTTON_MASKS = {
    "a": 0x000800000000,
    "b": 0x000400000000,
    "x": 0x000200000000,
    "y": 0x000100000000,
    "r": 0x004000000000,
    "l": 0x000000400000,
    "dpad_up": 0x000000020000,
    "dpad_right": 0x000000040000,
    "dpad_down": 0x000000010000,
    "dpad_left": 0x000000080000,
    "home": 0x000010000000,
    "minus": 0x000001000000,
    "plus": 0x000002000000,
    "r3": 0x000004000000,
    "l3": 0x000008000000,
    "capture": 0x000020000000,
    "c": 0x000040000000,
    "zl": 0x000000800000,
    "zr": 0x008000000000,
    "gl": 0x000000000200,
    "gr": 0x000000000100,
}

FACE_BUTTON_LAYOUTS = {
    # Preserve the letters printed on the Nintendo controller.
    "nintendo": {"a": "a", "b": "b", "x": "x", "y": "y"},
    # Preserve Xbox button positions (bottom/right/left/top).
    "xbox": {"a": "b", "b": "a", "x": "y", "y": "x"},
}


@dataclass(frozen=True, slots=True)
class ControllerState:
    pressed: frozenset[str]
    left_x: int
    left_y: int
    right_x: int
    right_y: int
    raw_left_x: int = 2048
    raw_left_y: int = 2048
    raw_right_x: int = 2048
    raw_right_y: int = 2048


def unpack_stick(packed: bytes) -> tuple[int, int]:
    """Return the controller's original unsigned 12-bit stick values."""
    if len(packed) != 3:
        raise ValueError("a packed stick must contain exactly 3 bytes")
    raw_x = ((packed[1] & 0x0F) << 8) | packed[0]
    raw_y = (packed[2] << 4) | ((packed[1] & 0xF0) >> 4)
    return raw_x, raw_y


def switch2_pro_product_id(manufacturer_data: Mapping[int, bytes]) -> int | None:
    """Return PID 0x2069 for a Nintendo Pro2 advert of any format revision."""
    data = manufacturer_data.get(NINTENDO_MANUFACTURER_ID)
    if data is None or len(data) < 7:
        return None
    if not data.startswith(SWITCH2_ADVERTISEMENT_PREFIX):
        return None
    product_id = int.from_bytes(data[5:7], "little")
    return product_id if product_id == SWITCH2_PRO_PRODUCT_ID else None


def decode_stick(packed: bytes, *, deadzone: float = 0.08, scale: float = 1.7) -> tuple[int, int]:
    """Decode two packed 12-bit axes into the signed XInput stick range."""
    raw_x, raw_y = unpack_stick(packed)
    x = (raw_x - 2048) / 2048.0
    y = (raw_y - 2048) / 2048.0

    if abs(x) < deadzone and abs(y) < deadzone:
        return 0, 0

    x = max(-1.0, min(1.0, x * scale))
    y = max(-1.0, min(1.0, y * scale))
    return round(x * 32767), round(y * 32767)


def parse_input_report(data: bytes | bytearray) -> ControllerState:
    """Parse the common buttons/sticks from a full Pro Controller 2 report."""
    if len(data) < 16:
        raise ValueError(f"input report is too short: {len(data)} bytes")

    button_bits = int.from_bytes(data[3:9], "big")
    pressed = frozenset(name for name, mask in BUTTON_MASKS.items() if button_bits & mask)
    left_packed = bytes(data[10:13])
    right_packed = bytes(data[13:16])
    left_x, left_y = decode_stick(left_packed)
    right_x, right_y = decode_stick(right_packed)
    raw_left_x, raw_left_y = unpack_stick(left_packed)
    raw_right_x, raw_right_y = unpack_stick(right_packed)
    return ControllerState(
        pressed,
        left_x,
        left_y,
        right_x,
        right_y,
        raw_left_x,
        raw_left_y,
        raw_right_x,
        raw_right_y,
    )
