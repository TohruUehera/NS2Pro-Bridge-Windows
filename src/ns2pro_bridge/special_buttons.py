"""Routing for Pro Controller 2 buttons that do not exist in XInput."""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterable, Mapping

SPECIAL_BUTTONS = ("capture", "c", "gl", "gr")

XINPUT_ACTIONS = {
    "xinput_guide": "home",
    "xinput_lb": "l",
    "xinput_rb": "r",
    "xinput_l3": "l3",
    "xinput_r3": "r3",
    "xinput_view": "minus",
    "xinput_menu": "plus",
}

NINTENDO_ACTIONS = {
    "native_capture": "capture",
    "native_c": "c",
    "native_gl": "gl",
    "native_gr": "gr",
}

KEY_CHORDS = {
    "key_f12": (0x7B,),
    "key_f13": (0x7C,),
    "key_f14": (0x7D,),
    "key_shift_tab": (0x10, 0x09),
}

DEFAULT_SPECIAL_MAPPINGS = {
    "capture": "key_f12",
    "c": "key_shift_tab",
    "gl": "key_f13",
    "gr": "key_f14",
}


def send_windows_key_chord(keys: tuple[int, ...]) -> None:
    """Emit one press/release chord without retaining any global key state."""
    if sys.platform != "win32":
        return
    import ctypes

    key_up = 0x0002
    user32 = ctypes.windll.user32
    for key in keys:
        user32.keybd_event(key, 0, 0, 0)
    for key in reversed(keys):
        user32.keybd_event(key, 0, key_up, 0)


class SpecialButtonRouter:
    """Edge-trigger keyboard actions and return held virtual-button aliases."""

    def __init__(
        self,
        mappings: Mapping[str, str] | None = None,
        key_sender: Callable[[tuple[int, ...]], None] = send_windows_key_chord,
    ) -> None:
        self._mappings = dict(DEFAULT_SPECIAL_MAPPINGS if mappings is None else mappings)
        self._key_sender = key_sender
        self._previous: set[str] = set()

    def route(self, pressed: Iterable[str]) -> set[str]:
        pressed_set = set(pressed)
        special_pressed = pressed_set.intersection(SPECIAL_BUTTONS)
        rising = special_pressed - self._previous
        aliases: set[str] = set()

        for physical in SPECIAL_BUTTONS:
            if physical not in special_pressed:
                continue
            action = self._mappings.get(physical, "disabled")
            alias = XINPUT_ACTIONS.get(action) or NINTENDO_ACTIONS.get(action)
            if action == "native_same":
                alias = physical
            if alias is not None:
                aliases.add(alias)

        for physical in SPECIAL_BUTTONS:
            if physical not in rising:
                continue
            action = self._mappings.get(physical, "disabled")
            chord = KEY_CHORDS.get(action)
            if chord is not None:
                self._key_sender(chord)

        self._previous = special_pressed
        return aliases

    def reset(self) -> None:
        self._previous.clear()
