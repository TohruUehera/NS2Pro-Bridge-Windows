"""Async Bluetooth LE session and reconnect loop."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from typing import Any

from .haptics import PRO_RUMBLE_PACKET_SIZE, build_pro_rumble_packet
from .protocol import (
    ACK_REPORT_UUID,
    INITIALIZATION_COMMANDS,
    INPUT_REPORT_UUID,
    NINTENDO_MANUFACTURER_ID,
    PRO_RUMBLE_UUID,
    WRITE_COMMAND_UUID,
    parse_input_report,
    switch2_pro_product_id,
)
from .radio import BluetoothRadioNotReady, require_bluetooth_radio
from .viiper_nintendo import ViiperNintendoPad, ViiperUnavailable
from .virtual_gamepad import VirtualGamepadUnavailable, VirtualXboxPad

EventCallback = Callable[[str, object], None]


def _windows_error_is(exc: BaseException, winerror: int) -> bool:
    """Inspect wrapped exceptions as Bleak/WinRT may preserve only a cause."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if getattr(current, "winerror", None) == winerror:
            return True
        current = current.__cause__ or current.__context__
    return False


def _winrt_address_type(device: Any) -> str | None:
    """Keep the public/random address type captured by the WinRT scanner."""
    details = getattr(device, "details", None)
    args = getattr(details, "adv", None) or getattr(details, "scan", None)
    address_type = getattr(args, "bluetooth_address_type", None)
    name = getattr(address_type, "name", str(address_type)).lower()
    if "public" in name:
        return "public"
    if "random" in name:
        return "random"
    return None


class BridgeWorker:
    """Own an asyncio loop in a background thread and emit UI-safe events."""

    def __init__(
        self,
        event_callback: EventCallback,
        face_layout: str = "nintendo",
        special_mappings: dict[str, str] | None = None,
        haptic_profile: str | None = "balanced",
        output_mode: str = "xbox",
    ) -> None:
        self._emit_callback = event_callback
        self._face_layout = face_layout
        self._special_mappings = special_mappings
        self._haptic_profile = haptic_profile
        if output_mode not in {"xbox", "nintendo"}:
            raise ValueError(f"unknown output mode: {output_mode}")
        self._output_mode = output_mode
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop_event: asyncio.Event | None = None
        self._rumble_event: asyncio.Event | None = None
        self._rumble_feedback = (0, 0)
        self._native_rumble_event: asyncio.Event | None = None
        self._native_rumble_packet = bytes(PRO_RUMBLE_PACKET_SIZE)
        self.packet_count = 0

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._thread = threading.Thread(target=self._thread_main, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._loop is not None and self._stop_event is not None:
            self._loop.call_soon_threadsafe(self._stop_event.set)

    def _emit(self, kind: str, value: object = "") -> None:
        self._emit_callback(kind, value)

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run())
        except Exception as exc:  # keep background failures visible in the GUI
            self._emit("error", f"后台线程异常：{type(exc).__name__}: {exc}")
        finally:
            self._emit("state", ("stopped", ""))

    async def _scan(self) -> Any | None:
        try:
            from bleak import BleakScanner
        except ImportError as exc:
            raise RuntimeError("缺少 bleak。请先运行 scripts\\setup.ps1。") from exc

        await require_bluetooth_radio()

        found = asyncio.Event()
        result: list[Any] = []
        unsupported_nintendo_adverts: set[str] = set()

        def on_advertisement(device: Any, advertisement: Any) -> None:
            if result:
                return
            if switch2_pro_product_id(advertisement.manufacturer_data) is None:
                raw = advertisement.manufacturer_data.get(NINTENDO_MANUFACTURER_ID)
                if raw:
                    encoded = bytes(raw).hex(" ").upper()
                    if encoded not in unsupported_nintendo_adverts:
                        unsupported_nintendo_adverts.add(encoded)
                        self._emit(
                            "log",
                            "发现未识别的 Nintendo BLE 广播："
                            f"{encoded}。如为官方 NS2 Pro，请随问题报告提交此值。",
                        )
                return
            result.append(device)
            found.set()

        scanner = BleakScanner(on_advertisement, scanning_mode="active")
        try:
            await scanner.start()
        except OSError as exc:
            # HRESULT 0x800710DF / WinError -2147020577: DEVICE_NOT_READY.
            if getattr(exc, "winerror", None) == -2147020577:
                raise BluetoothRadioNotReady(
                    "Windows 报告蓝牙设备未就绪。请先关闭“添加设备”窗口，"
                    "将蓝牙开关关闭再打开；若仍失败，请重启电脑后重试。"
                ) from exc
            raise
        try:
            found_task = asyncio.create_task(found.wait())
            stop_task = asyncio.create_task(self._stop_event.wait())
            done, pending = await asyncio.wait(
                {found_task, stop_task},
                timeout=30,
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            if not done or stop_task in done:
                return None
            return result[0]
        finally:
            await scanner.stop()

    async def _initialize(self, client: Any) -> None:
        for index, command in enumerate(INITIALIZATION_COMMANDS):
            last_error: Exception | None = None
            for attempt in range(1, 4):
                try:
                    await client.write_gatt_char(
                        WRITE_COMMAND_UUID, command
                    )
                    last_error = None
                    if attempt > 1:
                        self._emit(
                            "log", f"初始化命令 {index + 1} 在第 {attempt} 次写入成功。"
                        )
                    break
                except Exception as exc:
                    last_error = exc
                    await asyncio.sleep(0.12 * attempt)
            if last_error is not None:
                raise RuntimeError(
                    f"初始化命令 {index + 1} 连续三次写入失败：{last_error}"
                ) from last_error
            await asyncio.sleep(0.08)

    def _receive_rumble_feedback(self, large_motor: int, small_motor: int) -> None:
        if self._loop is None or self._rumble_event is None:
            return

        def update_feedback() -> None:
            self._rumble_feedback = (large_motor, small_motor)
            self._rumble_event.set()

        self._loop.call_soon_threadsafe(update_feedback)

    def _receive_native_rumble(self, packet: bytes) -> None:
        if self._loop is None or self._native_rumble_event is None:
            return

        def update_feedback() -> None:
            self._native_rumble_packet = packet
            self._native_rumble_event.set()

        self._loop.call_soon_threadsafe(update_feedback)

    async def _haptic_loop(self, client: Any) -> None:
        """Stream only the newest XInput feedback at the BLE-safe 15 ms cadence."""
        counter = 0
        was_active = False
        try:
            while not self._stop_event.is_set() and client.is_connected:
                large_motor, small_motor = self._rumble_feedback
                active = bool(large_motor or small_motor)
                if active or was_active:
                    packet = build_pro_rumble_packet(
                        large_motor,
                        small_motor,
                        counter,
                        profile_name=self._haptic_profile or "balanced",
                    )
                    await client.write_gatt_char(PRO_RUMBLE_UUID, packet)
                    if active:
                        counter = (counter + 1) & 0x0F
                    was_active = active

                self._rumble_event.clear()
                try:
                    await asyncio.wait_for(
                        self._rumble_event.wait(), timeout=0.015 if active else 1.0
                    )
                except TimeoutError:
                    pass
        except Exception as exc:
            self._emit("log", f"HD Rumble 2 输出已停用（按键连接保持）：{exc}")
        finally:
            # Cancellation and user-initiated release must not leave an actuator
            # sustaining its last non-zero frame.
            if client.is_connected:
                try:
                    await client.write_gatt_char(
                        PRO_RUMBLE_UUID,
                        build_pro_rumble_packet(0, 0, counter),
                    )
                except Exception:
                    pass

    async def _native_haptic_loop(self, client: Any) -> None:
        """Pass the newest raw Nintendo HD Rumble 2 report through at BLE pace."""
        try:
            while not self._stop_event.is_set() and client.is_connected:
                await self._native_rumble_event.wait()
                self._native_rumble_event.clear()
                await client.write_gatt_char(
                    PRO_RUMBLE_UUID, self._native_rumble_packet
                )
                await asyncio.sleep(0.015)
        except Exception as exc:
            self._emit("log", f"原生 HD Rumble 2 直通已停用（按键连接保持）：{exc}")
        finally:
            if client.is_connected:
                try:
                    await client.write_gatt_char(
                        PRO_RUMBLE_UUID,
                        build_pro_rumble_packet(0, 0, 0),
                    )
                except Exception:
                    pass

    async def _run(self) -> None:
        try:
            from bleak import BleakClient
        except ImportError as exc:
            raise RuntimeError("缺少 bleak。请先运行 scripts\\setup.ps1。") from exc

        self._loop = asyncio.get_running_loop()
        self._stop_event = asyncio.Event()
        self._rumble_event = asyncio.Event()
        self._native_rumble_event = asyncio.Event()

        if self._output_mode == "xbox":
            try:
                gamepad = VirtualXboxPad(self._face_layout, self._special_mappings)
            except VirtualGamepadUnavailable as exc:
                self._emit("error", str(exc))
                return
            self._emit("log", "虚拟 Xbox 360 手柄已创建。")
            if self._haptic_profile is not None:
                gamepad.set_feedback_callback(self._receive_rumble_feedback)
        else:
            gamepad = ViiperNintendoPad(
                output_callback=(
                    self._receive_native_rumble
                    if self._haptic_profile is not None
                    else None
                ),
                log_callback=lambda message: self._emit("log", message),
                special_mappings=self._special_mappings,
            )
            try:
                await asyncio.to_thread(gamepad.start)
            except (ViiperUnavailable, OSError, ValueError, KeyError) as exc:
                self._emit(
                    "error",
                    "无法创建 Nintendo 虚拟手柄。请确认 viiper-haptic.exe 位于 "
                    f"runtime 文件夹且 USBIP 驱动已安装。\n\n详细信息：{exc}",
                )
                return
            self._emit("log", "虚拟 Nintendo Switch 2 Pro Controller 已创建。")
        try:
            while not self._stop_event.is_set():
                self._emit("state", ("scanning", ""))
                self._emit("log", "正在扫描 PID 0x2069；请持续按住手柄顶部 SYNC 键。")
                try:
                    device = await self._scan()
                except BluetoothRadioNotReady as exc:
                    self._emit("error", str(exc))
                    return
                if device is None:
                    if not self._stop_event.is_set():
                        self._emit("log", "30 秒内未发现手柄，将自动继续扫描。")
                    continue

                address = getattr(device, "address", "未知地址")
                self._emit("state", ("connecting", address))
                self._emit("log", f"发现 Switch 2 Pro（{address}），正在建立 GATT 连接……")
                disconnected = asyncio.Event()

                def on_disconnect(_client: Any) -> None:
                    self._loop.call_soon_threadsafe(disconnected.set)

                winrt_options: dict[str, object] = {"use_cached_services": False}
                address_type = _winrt_address_type(device)
                if address_type is not None:
                    winrt_options["address_type"] = address_type
                stage = "打开 BLE 设备 / 建立 GATT 会话"
                client = BleakClient(
                    device,
                    disconnected_callback=on_disconnect,
                    timeout=25,
                    pair=False,
                    winrt=winrt_options,
                )

                # Bleak opens the WinRT object and immediately discovers services.
                # Pro2 is more reliable with the same 500 ms settling period used
                # by the reference bridge. Keep this narrowly guarded for Bleak's
                # WinRT backend so other platforms are unaffected.
                backend = getattr(client, "_backend", None)
                get_services = getattr(backend, "_get_services", None)
                if get_services is not None:
                    first_discovery = True

                    async def settled_get_services(*args: Any, **kwargs: Any) -> Any:
                        nonlocal first_discovery, stage
                        if first_discovery:
                            first_discovery = False
                            stage = "等待 BLE 链路稳定（500 ms）"
                            await asyncio.sleep(0.5)
                        stage = "未缓存 GATT 服务发现"
                        return await get_services(*args, **kwargs)

                    backend._get_services = settled_get_services
                try:
                    await client.connect()
                    stage = "校验 GATT 特征"
                    characteristics = {
                        characteristic.uuid.lower()
                        for service in client.services
                        for characteristic in service.characteristics
                    }
                    missing = {
                        INPUT_REPORT_UUID,
                        WRITE_COMMAND_UUID,
                        ACK_REPORT_UUID,
                    } - characteristics
                    if missing:
                        raise RuntimeError(
                            "GATT 服务尚未就绪，缺少：" + ", ".join(sorted(missing))
                        )

                    haptics_available = PRO_RUMBLE_UUID in characteristics
                    haptics_active = bool(
                        haptics_available and self._haptic_profile is not None
                    )

                    stage = "订阅命令 ACK"
                    await client.start_notify(ACK_REPORT_UUID, lambda _sender, _data: None)
                    stage = "发送 Pro2 初始化序列"
                    await self._initialize(client)
                    if haptics_active and self._output_mode == "nintendo":
                        self._emit("log", "原生 HD Rumble 2 左/右波形转换直通已启用。")
                    elif haptics_active:
                        self._emit(
                            "log",
                            "HD Rumble 2 合成已启用：XInput 低/高频反馈将镜像到左右执行器。",
                        )
                    elif self._haptic_profile is not None:
                        self._emit("log", "未发现 CC48 原始震动特征，震动已自动关闭。")

                    def on_input(_sender: Any, data: bytearray) -> None:
                        try:
                            gamepad.update(parse_input_report(data))
                            self.packet_count += 1
                        except ValueError:
                            return

                    stage = "订阅 FD2 输入通知"
                    await client.start_notify(INPUT_REPORT_UUID, on_input)
                    self._emit("state", ("connected", address))
                    visible_name = (
                        "Nintendo Switch 2 Pro Controller"
                        if self._output_mode == "nintendo"
                        else "Xbox 360 Controller"
                    )
                    self._emit("log", f"连接成功：Steam 现在应能看到 {visible_name}。")

                    haptic_task = None
                    if haptics_active:
                        if self._output_mode == "nintendo":
                            self._native_rumble_packet = bytes(PRO_RUMBLE_PACKET_SIZE)
                            haptic_task = asyncio.create_task(self._native_haptic_loop(client))
                        else:
                            self._rumble_feedback = (0, 0)
                            haptic_task = asyncio.create_task(self._haptic_loop(client))
                    stop_task = asyncio.create_task(self._stop_event.wait())
                    disconnect_task = asyncio.create_task(disconnected.wait())
                    session_tasks = {stop_task, disconnect_task}
                    _, pending = await asyncio.wait(
                        session_tasks, return_when=asyncio.FIRST_COMPLETED
                    )
                    for task in pending:
                        task.cancel()
                    if haptic_task is not None:
                        if not haptic_task.done():
                            haptic_task.cancel()
                        try:
                            await haptic_task
                        except asyncio.CancelledError:
                            pass
                except Exception as exc:
                    if _windows_error_is(exc, -2147023673):
                        self._emit(
                            "log",
                            f"连接阶段“{stage}”被 Windows 取消（0x800704C7）。这不是你"
                            "主动取消：请关闭系统“添加设备”窗口和配对通知，不要点击配对；"
                            "让 NS2 休眠，并让手柄持续保持 SYNC 闪灯。程序将在 5 秒后按"
                            "广播中的正确地址类型重新扫描。",
                        )
                        await asyncio.sleep(5)
                    else:
                        self._emit(
                            "log",
                            f"连接失败（阶段：{stage}）：{type(exc).__name__}: {exc}",
                        )
                        await asyncio.sleep(1.5)
                finally:
                    if client.is_connected:
                        try:
                            await client.disconnect()
                        except Exception:
                            pass

                if not self._stop_event.is_set():
                    self._emit("log", "连接已断开；程序将重新扫描。")
        finally:
            if self._output_mode == "nintendo":
                await asyncio.to_thread(gamepad.close)
            else:
                gamepad.close()
            self._emit("log", "虚拟手柄已移除。")
