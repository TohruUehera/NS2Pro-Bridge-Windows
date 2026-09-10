"""Windows Bluetooth radio readiness checks."""

from __future__ import annotations


class BluetoothRadioNotReady(RuntimeError):
    pass


async def bluetooth_radio_state() -> str:
    """Return ``on``, ``off``, ``disabled`` or ``unavailable`` on Windows."""
    try:
        from winrt.windows.devices.radios import Radio, RadioKind, RadioState
    except ImportError:
        return "unavailable"

    radios = await Radio.get_radios_async()
    for radio in radios:
        if radio.kind == RadioKind.BLUETOOTH:
            if radio.state == RadioState.ON:
                return "on"
            if radio.state == RadioState.OFF:
                return "off"
            if radio.state == RadioState.DISABLED:
                return "disabled"
            return "unknown"
    return "unavailable"


async def require_bluetooth_radio() -> None:
    state = await bluetooth_radio_state()
    if state == "on":
        return
    if state == "off":
        raise BluetoothRadioNotReady(
            "Windows 蓝牙开关当前为关闭。请在“设置 → 蓝牙和设备”中打开蓝牙，然后重试。"
        )
    if state == "disabled":
        raise BluetoothRadioNotReady(
            "Windows 蓝牙射频被系统或硬件禁用。请解除飞行模式/硬件禁用后重试。"
        )
    if state == "unavailable":
        raise BluetoothRadioNotReady(
            "Windows 没有提供可用的 Bluetooth LE 射频。请重新启用蓝牙适配器或重启电脑。"
        )
    raise BluetoothRadioNotReady(f"Windows 蓝牙射频状态异常：{state}")

