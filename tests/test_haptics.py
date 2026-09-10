from __future__ import annotations

import pytest

from ns2pro_bridge.haptics import (
    HAPTIC_PROFILES,
    build_pro_rumble_packet,
    encode_hd_rumble2_frame,
    xinput_to_hd_rumble2_frame,
)


def decode_frame(frame: bytes) -> tuple[int, int, int, int]:
    value = int.from_bytes(frame, "little")
    return (
        value & 0x3FF,
        (value >> 10) & 0x3FF,
        (value >> 20) & 0x3FF,
        (value >> 30) & 0x3FF,
    )


def test_hd_rumble2_frame_packs_four_fields() -> None:
    frame = encode_hd_rumble2_frame(160, 500, 320, 250)
    assert len(frame) == 5
    assert decode_frame(frame) == (160, 500, 320, 250)


def test_encoder_clamps_protocol_fields() -> None:
    assert decode_frame(encode_hd_rumble2_frame(-1, 2000, 900, -4)) == (
        0,
        1023,
        511,
        0,
    )


def test_zero_xinput_feedback_produces_stop_frame() -> None:
    assert xinput_to_hd_rumble2_frame(0, 0) == bytes(5)
    packet = build_pro_rumble_packet(0, 0, 7)
    assert len(packet) == 33
    assert packet[1] == packet[17] == 0x57
    assert decode_frame(packet[2:7]) == (0x0E1, 0, 0x1E1, 0)
    assert packet[2:7] == packet[7:12] == packet[12:17]


@pytest.mark.parametrize("profile_name", ("balanced", "strong"))
def test_full_xinput_feedback_respects_selected_safety_limit(profile_name: str) -> None:
    profile = HAPTIC_PROFILES[profile_name]
    low_frequency, low_amplitude, high_frequency, high_amplitude = decode_frame(
        xinput_to_hd_rumble2_frame(255, 255, profile_name=profile_name)
    )
    assert (low_frequency, high_frequency) == (
        profile.low_frequency,
        profile.high_frequency,
    )
    assert low_amplitude == high_amplitude == profile.maximum_amplitude


def test_pro_packet_mirrors_frame_and_sequence_to_both_actuators() -> None:
    packet = build_pro_rumble_packet(255, 64, 0x1D)
    assert len(packet) == 33
    assert packet[1] == packet[17] == 0x5D
    assert packet[2:7] == packet[18:23]
    assert any(packet[2:7])


def test_unknown_haptic_profile_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown haptic profile"):
        xinput_to_hd_rumble2_frame(1, 1, profile_name="native-magic")
