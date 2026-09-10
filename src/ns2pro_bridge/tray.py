"""Native Windows notification-area icon with no third-party GUI runtime."""

from __future__ import annotations

import ctypes
import os
import threading
from collections.abc import Callable
from ctypes import wintypes

WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
WM_CONTEXTMENU = 0x007B
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
WM_NULL = 0x0000
WM_TRAY_CALLBACK = 0x0400 + 41

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIM_SETVERSION = 0x00000004
NOTIFYICON_VERSION_4 = 4
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NIF_INFO = 0x00000010
NIIF_INFO = 0x00000001

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
MF_GRAYED = 0x00000001
TPM_RIGHTBUTTON = 0x00000002
TPM_RETURNCMD = 0x00000100

CMD_SHOW = 1001
CMD_DISCONNECT = 1002
CMD_EXIT = 1003
IDI_APPLICATION = 32512


class GUID(ctypes.Structure):
    _fields_ = (
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    )


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = (
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HANDLE),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", GUID),
        ("hBalloonIcon", wintypes.HANDLE),
    )


LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)


class WNDCLASSW(ctypes.Structure):
    _fields_ = (
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HANDLE),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HANDLE),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    )


class WindowsTrayIcon:
    """Own a hidden Win32 window and Shell_NotifyIcon message loop."""

    def __init__(
        self,
        title: str,
        on_action: Callable[[str], None],
        disconnect_enabled: Callable[[], bool],
    ) -> None:
        if os.name != "nt":
            raise OSError("Windows notification area is only available on Windows")
        self._title = title
        self._on_action = on_action
        self._disconnect_enabled = disconnect_enabled
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._hwnd: int | None = None
        self._error: BaseException | None = None
        self._class_name = f"NS2ProBridgeTray_{os.getpid()}_{id(self):x}"
        self._wndproc = WNDPROC(self._window_proc)

        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)
        self._kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        self._user32.CreateWindowExW.argtypes = (
            wintypes.DWORD,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            wintypes.HANDLE,
            wintypes.HINSTANCE,
            wintypes.LPVOID,
        )
        self._user32.DefWindowProcW.argtypes = (
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        self._user32.DefWindowProcW.restype = LRESULT
        self._user32.LoadIconW.restype = wintypes.HANDLE
        self._user32.CreatePopupMenu.restype = wintypes.HANDLE
        self._user32.RegisterClassW.argtypes = (ctypes.POINTER(WNDCLASSW),)
        self._user32.UnregisterClassW.argtypes = (
            wintypes.LPCWSTR,
            wintypes.HINSTANCE,
        )
        self._user32.CreateWindowExW.restype = wintypes.HWND
        self._shell32.Shell_NotifyIconW.argtypes = (
            wintypes.DWORD,
            ctypes.POINTER(NOTIFYICONDATAW),
        )
        self._shell32.Shell_NotifyIconW.restype = wintypes.BOOL

    @staticmethod
    def _safe_text(value: str, limit: int) -> str:
        return value.replace("\0", " ")[: limit - 1]

    def _notification_data(self, flags: int) -> NOTIFYICONDATAW:
        data = NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        data.hWnd = self._hwnd
        data.uID = 1
        data.uFlags = flags
        data.uCallbackMessage = WM_TRAY_CALLBACK
        data.hIcon = self._user32.LoadIconW(None, IDI_APPLICATION)
        data.szTip = self._safe_text(self._title, 128)
        return data

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._ready.clear()
        self._error = None
        self._thread = threading.Thread(
            target=self._run, name="NS2ProBridgeTray", daemon=True
        )
        self._thread.start()
        if not self._ready.wait(timeout=3):
            raise OSError("系统托盘线程启动超时")
        if self._error is not None:
            raise OSError(f"系统托盘初始化失败：{self._error}") from self._error

    def _run(self) -> None:
        instance = self._kernel32.GetModuleHandleW(None)
        try:
            window_class = WNDCLASSW()
            window_class.lpfnWndProc = self._wndproc
            window_class.hInstance = instance
            window_class.lpszClassName = self._class_name
            if not self._user32.RegisterClassW(ctypes.byref(window_class)):
                raise ctypes.WinError(ctypes.get_last_error())
            hwnd = self._user32.CreateWindowExW(
                0, self._class_name, self._class_name, 0,
                0, 0, 0, 0, None, None, instance, None,
            )
            if not hwnd:
                raise ctypes.WinError(ctypes.get_last_error())
            self._hwnd = hwnd
            data = self._notification_data(NIF_MESSAGE | NIF_ICON | NIF_TIP)
            if not self._shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(data)):
                raise ctypes.WinError(ctypes.get_last_error())
            data.uVersion = NOTIFYICON_VERSION_4
            self._shell32.Shell_NotifyIconW(NIM_SETVERSION, ctypes.byref(data))
            self._ready.set()

            message = wintypes.MSG()
            while self._user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                self._user32.TranslateMessage(ctypes.byref(message))
                self._user32.DispatchMessageW(ctypes.byref(message))
        except BaseException as exc:
            self._error = exc
            self._ready.set()
        finally:
            if self._hwnd:
                data = self._notification_data(0)
                self._shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(data))
                self._hwnd = None
            self._user32.UnregisterClassW(self._class_name, instance)

    def _window_proc(self, hwnd, message, wparam, lparam) -> int:
        try:
            if message == WM_TRAY_CALLBACK:
                event = int(lparam) & 0xFFFF
                if event == WM_LBUTTONDBLCLK:
                    self._on_action("show")
                    return 0
                if event in {WM_RBUTTONUP, WM_CONTEXTMENU}:
                    self._show_menu(hwnd)
                    return 0
            elif message == WM_COMMAND:
                self._dispatch_command(int(wparam) & 0xFFFF)
                return 0
            elif message == WM_DESTROY:
                self._user32.PostQuitMessage(0)
                return 0
        except Exception:
            return 0
        return self._user32.DefWindowProcW(hwnd, message, wparam, lparam)

    def _show_menu(self, hwnd) -> None:
        menu = self._user32.CreatePopupMenu()
        if not menu:
            return
        try:
            self._user32.AppendMenuW(menu, MF_STRING, CMD_SHOW, "显示主窗口")
            flags = MF_STRING if self._disconnect_enabled() else MF_STRING | MF_GRAYED
            self._user32.AppendMenuW(menu, flags, CMD_DISCONNECT, "释放给 NS2")
            self._user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            self._user32.AppendMenuW(menu, MF_STRING, CMD_EXIT, "完全退出")
            point = wintypes.POINT()
            self._user32.GetCursorPos(ctypes.byref(point))
            self._user32.SetForegroundWindow(hwnd)
            command = self._user32.TrackPopupMenu(
                menu, TPM_RIGHTBUTTON | TPM_RETURNCMD,
                point.x, point.y, 0, hwnd, None,
            )
            if command:
                self._dispatch_command(command)
            self._user32.PostMessageW(hwnd, WM_NULL, 0, 0)
        finally:
            self._user32.DestroyMenu(menu)

    def _dispatch_command(self, command: int) -> None:
        action = {
            CMD_SHOW: "show",
            CMD_DISCONNECT: "disconnect",
            CMD_EXIT: "exit",
        }.get(command)
        if action is not None:
            self._on_action(action)

    def set_title(self, title: str) -> None:
        self._title = title
        if self._hwnd:
            data = self._notification_data(NIF_TIP)
            self._shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(data))

    def notify(self, message: str, title: str) -> None:
        if not self._hwnd:
            return
        data = self._notification_data(NIF_INFO)
        data.szInfo = self._safe_text(message, 256)
        data.szInfoTitle = self._safe_text(title, 64)
        data.dwInfoFlags = NIIF_INFO
        self._shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(data))

    def stop(self) -> None:
        hwnd = self._hwnd
        if hwnd:
            self._user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=3)
        self._thread = None
