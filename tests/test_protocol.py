from __future__ import annotations

import pytest

from ns2pro_bridge.protocol import (
    BUTTON_MASKS,
    NINTENDO_MANUFACTURER_ID,
    SWITCH2_PRO_PRODUCT_ID,
    decode_stick,
    parse_input_report,
    switch2_pro_product_id,
)


def pack_stick(x: int, y: int) -> bytes:
    return bytes((x & 0xFF, ((x >> 8) & 0x0F) | ((y & 0x0F) << 4), (y >> 4) & 0xFF))


def make_report(buttons: int = 0, left: tuple[int, int] = (2048, 2048), right: tuple[int, int] = (2048, 2048)) -> bytes:
    report = bytearray(16)
    report[3:9] = buttons.to_bytes(6, "big")
    report[10:13] = pack_stick(*left)
    report[13:16] = pack_stick(*right)
    return bytes(report)


def test_matches_exact_switch2_pro_advertisement() -> None:
    data = bytes((0x01, 0x00, 0x03, 0x7E, 0x05, 0x69, 0x20, 0xAA))
    assert switch2_pro_product_id({NINTENDO_MANUFACTURER_ID: data}) == SWITCH2_PRO_PRODUCT_ID


def test_accepts_updated_advertisement_format_revision() -> None:
    data = bytes((0x01, 0x00, 0x03, 0x7E, 0x7F, 0x69, 0x20, 0xAA))
    assert switch2_pro_product_id({NINTENDO_MANUFACTURER_ID: data}) == SWITCH2_PRO_PRODUCT_ID


@pytest.mark.parametrize(
    "data",
    (
        b"",
        bytes((0x01, 0x00, 0x03, 0x7E, 0x05, 0x60, 0x20)),
        bytes((0x01, 0x00, 0x02, 0x7E, 0x05, 0x69, 0x20)),
    ),
)
def test_rejects_other_or_malformed_advertisements(data: bytes) -> None:
    assert switch2_pro_product_id({NINTENDO_MANUFACTURER_ID: data}) is None


def test_rejects_other_manufacturer() -> None:
    data = bytes((0x01, 0x00, 0x03, 0x7E, 0x05, 0x69, 0x20))
    assert switch2_pro_product_id({0x004C: data}) is None


def test_centered_stick_is_zero() -> None:
    assert decode_stick(pack_stick(2048, 2048)) == (0, 0)


def test_stick_values_are_scaled_and_clamped() -> None:
    assert decode_stick(pack_stick(4095, 4095)) == (32767, 32767)
    assert decode_stick(pack_stick(0, 0)) == (-32767, -32767)


def test_small_stick_motion_is_deadzoned() -> None:
    assert decode_stick(pack_stick(2100, 1990)) == (0, 0)


def test_report_decodes_buttons_and_both_sticks() -> None:
    masks = BUTTON_MASKS["a"] | BUTTON_MASKS["zl"] | BUTTON_MASKS["dpad_left"] | BUTTON_MASKS["gl"]
    state = parse_input_report(make_report(masks, (4095, 2048), (2048, 0)))
    assert state.pressed == frozenset({"a", "zl", "dpad_left", "gl"})
    assert state.left_x == 32767
    assert state.left_y == 0
    assert state.right_x == 0
    assert state.right_y == -32767
    assert (state.raw_left_x, state.raw_left_y) == (4095, 2048)
    assert (state.raw_right_x, state.raw_right_y) == (2048, 0)


def test_short_report_is_rejected() -> None:
    with pytest.raises(ValueError, match="too short"):
        parse_input_report(bytes(15))


def test_bad_stick_size_is_rejected() -> None:
    with pytest.raises(ValueError, match="exactly 3"):
        decode_stick(b"\x00\x00")
