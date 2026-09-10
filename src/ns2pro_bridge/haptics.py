"""HD Rumble 2 synthesis for XInput force-feedback values.

XInput exposes one low-frequency (large) and one high-frequency (small)
motor value.  A Pro Controller 2 actuator accepts a five-byte frame holding
low/high frequency and amplitude fields.  We preserve those two frequency
bands and mirror the result to the controller's left and right actuators.
"""

from __future__ import annotations

from dataclasses import dataclass

FREQUENCY_MAX = 0x1FF
AMPLITUDE_MAX = 0x3FF
PRO_RUMBLE_PACKET_SIZE = 33


@dataclass(frozen=True, slots=True)
class HapticProfile:
    low_frequency: int
    high_frequency: int
    maximum_amplitude: int
    gamma: float = 1.25


HAPTIC_PROFILES = {
    # The conservative default stays below half of the protocol amplitude
    # range to reduce tapping/noise during abrupt XInput changes.
    "balanced": HapticProfile(160, 320, 500, 1.25),
    "strong": HapticProfile(180, 360, 800, 1.15),
}


def _clamp(value: int, maximum: int) -> int:
    return max(0, min(maximum, int(value)))


def encode_hd_rumble2_frame(
    low_frequency: int,
    low_amplitude: int,
    high_frequency: int,
    high_amplitude: int,
) -> bytes:
    """Pack the four HD Rumble 2 fields into one five-byte LRA frame."""
    value = _clamp(low_frequency, FREQUENCY_MAX)
    value |= _clamp(low_amplitude, AMPLITUDE_MAX) << 10
    value |= _clamp(high_frequency, FREQUENCY_MAX) << 20
    value |= _clamp(high_amplitude, AMPLITUDE_MAX) << 30
    return value.to_bytes(5, "little")


def _scale_xinput(value: int, profile: HapticProfile) -> int:
    normalized = _clamp(value, 255) / 255.0
    return round((normalized ** profile.gamma) * profile.maximum_amplitude)


def xinput_to_hd_rumble2_frame(
    large_motor: int,
    small_motor: int,
    *,
    profile_name: str = "balanced",
) -> bytes:
    """Convert XInput's low/high motor strengths to one HD Rumble 2 frame."""
    try:
        profile = HAPTIC_PROFILES[profile_name]
    except KeyError as exc:
        raise ValueError(f"unknown haptic profile: {profile_name}") from exc

    low_amplitude = _scale_xinput(large_motor, profile)
    high_amplitude = _scale_xinput(small_motor, profile)
    if low_amplitude == 0 and high_amplitude == 0:
        return bytes(5)
    return encode_hd_rumble2_frame(
        profile.low_frequency,
        low_amplitude,
        profile.high_frequency,
        high_amplitude,
    )


def build_pro_rumble_packet(
    large_motor: int,
    small_motor: int,
    counter: int,
    *,
    profile_name: str = "balanced",
) -> bytes:
    """Build the 33-byte raw-rumble GATT packet used by Pro Controller 2.

    XInput has frequency bands rather than actuator-side data, so the same
    synthesized low/high frame is sent to both physical actuators.
    """
    frame = xinput_to_hd_rumble2_frame(
        large_motor, small_motor, profile_name=profile_name
    )
    packet = bytearray(PRO_RUMBLE_PACKET_SIZE)
    neutral = encode_hd_rumble2_frame(0x0E1, 0, 0x1E1, 0)
    sequence = 0x50 | (counter & 0x0F)
    for offset in (1, 17):
        packet[offset] = sequence
        packet[offset + 1 : offset + 6] = frame if any(frame) else neutral
        packet[offset + 6 : offset + 11] = neutral
        packet[offset + 11 : offset + 16] = neutral
    return bytes(packet)


def hid_switch_frame_to_ble(frame: bytes) -> bytes:
    """Convert a five-byte Switch USB HID rumble frame to the BLE encoding."""
    if len(frame) != 5:
        raise ValueError("a Switch HID rumble frame must contain exactly 5 bytes")
    high_frequency = frame[0] | ((frame[1] & 0x03) << 8)
    high_amplitude = ((frame[1] & 0xFC) << 4) | ((frame[2] & 0x0F) << 12)
    low_frequency = ((frame[2] & 0xF0) >> 4) | ((frame[3] & 0x3F) << 4)
    low_amplitude = (frame[3] & 0xC0) | (frame[4] << 8)

    def scale(value: int) -> int:
        return max(0, min(AMPLITUDE_MAX, round(value * AMPLITUDE_MAX / 29000)))

    return encode_hd_rumble2_frame(
        low_frequency,
        scale(low_amplitude),
        high_frequency,
        scale(high_amplitude),
    )


def build_pro_rumble_packet_from_hid_sides(
    left: bytes, right: bytes, counter: int
) -> bytes:
    """Convert VIIPER's two 16-byte HID sides to a physical Pro2 BLE packet."""
    if len(left) != 16 or len(right) != 16:
        raise ValueError("each Switch HID rumble side must contain 16 bytes")
    neutral = encode_hd_rumble2_frame(0x0E1, 0, 0x1E1, 0)
    packet = bytearray(PRO_RUMBLE_PACKET_SIZE)
    sequence = 0x50 | (counter & 0x0F)
    for offset, side in ((1, left), (17, right)):
        packet[offset] = sequence
        packet[offset + 1 : offset + 6] = hid_switch_frame_to_ble(side[1:6])
        packet[offset + 6 : offset + 11] = neutral
        packet[offset + 11 : offset + 16] = neutral
    return bytes(packet)
