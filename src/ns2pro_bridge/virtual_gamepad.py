"""Virtual Xbox 360 output backed by vgamepad/ViGEmBus."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from .protocol import ControllerState, FACE_BUTTON_LAYOUTS
from .special_buttons import SpecialButtonRouter


class VirtualGamepadUnavailable(RuntimeError):
    pass


class VirtualXboxPad:
    def __init__(
        self,
        face_layout: str = "nintendo",
        special_mappings: Mapping[str, str] | None = None,
    ) -> None:
        if face_layout not in FACE_BUTTON_LAYOUTS:
            raise ValueError(f"unknown face-button layout: {face_layout}")
        try:
            import vgamepad as vg
        except Exception as exc:  # vgamepad raises plain Exception when the bus is absent
            raise VirtualGamepadUnavailable(
                "无法创建虚拟手柄。请安装 ViGEmBus 1.22.0，并重新启动电脑。"
            ) from exc

        self._vg = vg
        try:
            self._pad = vg.VX360Gamepad()
        except Exception as exc:
            raise VirtualGamepadUnavailable(
                "ViGEmBus 未安装、未启动或与系统不兼容。"
            ) from exc
        self._face_layout = FACE_BUTTON_LAYOUTS[face_layout]
        self._special_router = SpecialButtonRouter(special_mappings)
        self._feedback_registered = False
        self._buttons = {
            "a": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
            "b": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
            "x": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
            "y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
            "l": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
            "r": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
            "dpad_up": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
            "dpad_right": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
            "dpad_down": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
            "dpad_left": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
            "home": vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,
            "minus": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
            "plus": vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
            "l3": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
            "r3": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
        }

    def update(self, state: ControllerState) -> None:
        logical_pressed = set(state.pressed)
        for physical, logical in self._face_layout.items():
            logical_pressed.discard(physical)
            if physical in state.pressed:
                logical_pressed.add(logical)

        logical_pressed.update(self._special_router.route(state.pressed))

        for name, button in self._buttons.items():
            if name in logical_pressed:
                self._pad.press_button(button)
            else:
                self._pad.release_button(button)

        self._pad.left_trigger(255 if "zl" in state.pressed else 0)
        self._pad.right_trigger(255 if "zr" in state.pressed else 0)
        self._pad.left_joystick(x_value=state.left_x, y_value=state.left_y)
        self._pad.right_joystick(x_value=state.right_x, y_value=state.right_y)
        self._pad.update()

    def set_feedback_callback(self, callback: Callable[[int, int], None]) -> None:
        # vgamepad checks the callback's complete signature, including names.
        def on_feedback(client, target, large_motor, small_motor, led_number, user_data):
            callback(int(large_motor), int(small_motor))

        self._pad.register_notification(on_feedback)
        self._feedback_registered = True

    def close(self) -> None:
        if self._feedback_registered:
            try:
                self._pad.unregister_notification()
            except Exception:
                pass
        self._special_router.reset()
        self._pad.reset()
        self._pad.update()
