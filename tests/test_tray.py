from __future__ import annotations

from ns2pro_bridge.tray import WindowsTrayIcon


def test_tray_text_is_nul_safe_and_bounded() -> None:
    assert WindowsTrayIcon._safe_text("A\0B", 10) == "A B"
    assert WindowsTrayIcon._safe_text("123456", 5) == "1234"
