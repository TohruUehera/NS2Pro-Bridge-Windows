"""Optional native Nintendo virtual-controller backend using VIIPER TCP API.

VIIPER remains a separate GPL-3.0 process.  This module is an independent TCP
client for its documented API and fixed-size ``ns2pro`` wire protocol.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

from .haptics import build_pro_rumble_packet_from_hid_sides
from .protocol import ControllerState

VIIPER_HOST = "127.0.0.1"
VIIPER_API_PORT = 3242
VIIPER_USB_PORT = 3241
INPUT_WIRE_SIZE = 28
OUTPUT_WIRE_SIZE = 34
OUTPUT_FLAG_RUMBLE = 0x01

NINTENDO_BUTTONS = {
    "b": 0x00000001,
    "a": 0x00000002,
    "y": 0x00000004,
    "x": 0x00000008,
    "r": 0x00000010,
    "zr": 0x00000020,
    "plus": 0x00000040,
    "r3": 0x00000080,
    "dpad_down": 0x00000100,
    "dpad_right": 0x00000200,
    "dpad_left": 0x00000400,
    "dpad_up": 0x00000800,
    "l": 0x00001000,
    "zl": 0x00002000,
    "minus": 0x00004000,
    "l3": 0x00008000,
    "home": 0x00010000,
    "capture": 0x00020000,
    "gr": 0x00040000,
    "gl": 0x00080000,
    "c": 0x00100000,
}


class ViiperUnavailable(RuntimeError):
    pass


def controller_state_to_viiper(state: ControllerState, timestamp_us: int = 0) -> bytes:
    buttons = 0
    for name in state.pressed:
        buttons |= NINTENDO_BUTTONS.get(name, 0)
    return struct.pack(
        "<IHHHHhhhhhhI",
        buttons,
        state.raw_left_x,
        state.raw_left_y,
        state.raw_right_x,
        state.raw_right_y,
        0,
        0,
        0,
        0,
        0,
        0,
        timestamp_us & 0xFFFFFFFF,
    )


def viiper_feedback_to_ble(data: bytes, counter: int = 0) -> bytes | None:
    """Translate VIIPER's two raw 16-byte rumble sides to Pro2 BLE layout."""
    if len(data) != OUTPUT_WIRE_SIZE:
        raise ValueError(f"VIIPER feedback must be {OUTPUT_WIRE_SIZE} bytes")
    if not data[32] & OUTPUT_FLAG_RUMBLE:
        return None
    return build_pro_rumble_packet_from_hid_sides(
        data[0:16], data[16:32], counter
    )


def _runtime_candidates() -> list[Path]:
    candidates: list[Path] = []
    configured = os.environ.get("NS2PRO_VIIPER_PATH")
    if configured:
        candidates.append(Path(configured))

    executable_dir = Path(sys.executable).resolve().parent
    project_dir = Path(__file__).resolve().parents[2]
    local_app_data = Path(os.environ.get("LOCALAPPDATA", executable_dir))
    bundled_dir = Path(getattr(sys, "_MEIPASS", project_dir))
    for root in (bundled_dir, executable_dir, project_dir):
        candidates.extend(
            (
                root / "runtime" / "viiper-haptic.exe",
                root / "viiper-haptic.exe",
            )
        )
    candidates.extend(
        (
            local_app_data / "VIIPER" / "viiper-haptic.exe",
            local_app_data / "VIIPER" / "viiper.exe",
        )
    )
    for name in ("viiper-haptic.exe", "viiper.exe"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    return candidates


def find_viiper_runtime() -> Path | None:
    for candidate in _runtime_candidates():
        try:
            if candidate.is_file():
                return candidate.resolve()
        except OSError:
            continue
    return None


class ViiperNintendoPad:
    def __init__(
        self,
        output_callback: Callable[[bytes], None] | None = None,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        self._output_callback = output_callback
        self._log = log_callback or (lambda _message: None)
        self._process: subprocess.Popen | None = None
        self._stream: socket.socket | None = None
        self._stream_lock = threading.Lock()
        self._reader: threading.Thread | None = None
        self._stopping = threading.Event()
        self._bus_id: int | None = None
        self._device_id: str | None = None
        self._feedback_counter = 0

    def _api_request(self, path: str, payload: str | None = None) -> str:
        request = path if not payload else f"{path} {payload}"
        with socket.create_connection((VIIPER_HOST, VIIPER_API_PORT), timeout=8) as sock:
            sock.sendall(request.encode("utf-8") + b"\0")
            chunks: list[bytes] = []
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
        response = b"".join(chunks).decode("utf-8", errors="replace").strip("\0\r\n ")
        if response:
            try:
                problem = json.loads(response)
            except json.JSONDecodeError:
                problem = None
            if isinstance(problem, dict) and isinstance(problem.get("status"), int):
                raise ViiperUnavailable(
                    f"VIIPER {problem['status']}：{problem.get('title', '')} "
                    f"{problem.get('detail', '')}".strip()
                )
        return response

    def _ping(self) -> bool:
        try:
            self._api_request("ping")
            return True
        except OSError:
            return False

    def _start_server(self) -> None:
        if self._ping():
            self._log("检测到已经运行的 VIIPER 服务。")
            return
        runtime = find_viiper_runtime()
        if runtime is None:
            raise ViiperUnavailable(
                "未找到 viiper-haptic.exe。请将参考项目的 VIIPER Haptic v0.8.0 "
                "放入程序旁的 runtime 文件夹，并先安装 USBIP 驱动。"
            )
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self._process = subprocess.Popen(
            [
                str(runtime),
                "server",
                f"--api.addr={VIIPER_HOST}:{VIIPER_API_PORT}",
                f"--usb.addr={VIIPER_HOST}:{VIIPER_USB_PORT}",
                "--api.auto-attach-local-client",
                "--api.auto-attach-windows-native",
                "--api.device-handler-connect-timeout=60s",
                "--update-notify=none",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                raise ViiperUnavailable("VIIPER 服务启动后立即退出；请检查 USBIP 运行时。")
            if self._ping():
                self._log(f"已启动 VIIPER：{runtime}")
                return
            time.sleep(0.2)
        raise ViiperUnavailable("VIIPER 服务在 8 秒内没有响应。")

    def start(self) -> None:
        try:
            self._start_server()
            created = json.loads(self._api_request("bus/create", "0"))
            self._bus_id = int(created["busId"])
            metadata = {
                "type": "ns2pro",
                "deviceSpecific": {
                    "serial_number": "NS2PRO-BRIDGE-00",
                    "input_interval_ms": 4,
                    "source_paced": True,
                },
            }
            device = json.loads(
                self._api_request(
                    f"bus/{self._bus_id}/add",
                    json.dumps(metadata, separators=(",", ":")),
                )
            )
            self._device_id = str(device["devId"])
            self._stream = socket.create_connection(
                (VIIPER_HOST, VIIPER_API_PORT), timeout=10
            )
            self._stream.settimeout(None)
            self._stream.sendall(
                f"bus/{self._bus_id}/{self._device_id}\0".encode("utf-8")
            )
            self._reader = threading.Thread(target=self._feedback_loop, daemon=True)
            self._reader.start()
            self._log(
                f"Nintendo 虚拟设备已创建：bus={self._bus_id} dev={self._device_id}"
            )
        except Exception:
            self.close()
            raise

    def _read_exact(self, size: int) -> bytes | None:
        data = bytearray()
        while len(data) < size and not self._stopping.is_set():
            stream = self._stream
            if stream is None:
                return None
            chunk = stream.recv(size - len(data))
            if not chunk:
                return None
            data.extend(chunk)
        return bytes(data) if len(data) == size else None

    def _feedback_loop(self) -> None:
        try:
            while not self._stopping.is_set():
                feedback = self._read_exact(OUTPUT_WIRE_SIZE)
                if feedback is None:
                    return
                packet = viiper_feedback_to_ble(feedback, self._feedback_counter)
                if packet is not None and self._output_callback is not None:
                    self._feedback_counter = (self._feedback_counter + 1) & 0x0F
                    self._output_callback(packet)
        except OSError as exc:
            if not self._stopping.is_set():
                self._log(f"VIIPER 反馈流已断开：{exc}")

    def update(self, state: ControllerState) -> None:
        stream = self._stream
        if stream is None:
            return
        timestamp_us = time.monotonic_ns() // 1000
        packet = controller_state_to_viiper(state, timestamp_us)
        with self._stream_lock:
            stream.sendall(packet)

    def close(self) -> None:
        self._stopping.set()
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            stream.close()
        if self._reader is not None and self._reader is not threading.current_thread():
            self._reader.join(timeout=1)
        self._reader = None

        if self._bus_id is not None and self._device_id is not None:
            try:
                self._api_request(f"bus/{self._bus_id}/remove", self._device_id)
            except Exception:
                pass
        if self._bus_id is not None:
            try:
                self._api_request("bus/remove", str(self._bus_id))
            except Exception:
                pass
        self._device_id = None
        self._bus_id = None

        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
