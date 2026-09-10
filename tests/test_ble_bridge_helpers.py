from __future__ import annotations

from types import SimpleNamespace

from ns2pro_bridge.ble_bridge import _windows_error_is, _winrt_address_type
from ns2pro_bridge.app import BridgeApp


def test_winrt_address_type_preserves_scanner_value() -> None:
    device = SimpleNamespace(
        details=SimpleNamespace(
            adv=SimpleNamespace(
                bluetooth_address_type=SimpleNamespace(name="RANDOM")
            ),
            scan=None,
        )
    )
    assert _winrt_address_type(device) == "random"


def test_cancel_hresult_is_found_through_wrapped_exception() -> None:
    windows_error = OSError("cancelled")
    windows_error.winerror = -2147023673
    wrapper = RuntimeError("Bleak operation failed")
    wrapper.__cause__ = windows_error
    assert _windows_error_is(wrapper, -2147023673)


def test_tray_icon_is_rgba_and_windows_icon_sized() -> None:
    image = BridgeApp._tray_image()
    assert image.mode == "RGBA"
    assert image.size == (64, 64)


def test_only_active_minimized_window_moves_to_tray() -> None:
    should_hide = BridgeApp._should_hide_to_tray
    assert should_hide("iconic", True, False, False)
    assert not should_hide("normal", True, False, False)
    assert not should_hide("iconic", False, False, False)
    assert not should_hide("iconic", True, True, False)
    assert not should_hide("iconic", True, False, True)
