"""Small Chinese-language Tk GUI for the BLE bridge."""

from __future__ import annotations

import os
import queue
import sys
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from . import __version__
from .ble_bridge import BridgeWorker
from .special_buttons import DEFAULT_SPECIAL_MAPPINGS

VIGEM_URL = "https://github.com/nefarius/ViGEmBus/releases/tag/v1.22.0"
VIIPER_URL = "https://github.com/LeonChrome/XinHeLianSheng-Pro2-Bridge/releases"

OUTPUT_LABELS = {
    "Xbox 360（兼容优先）": "xbox",
    "Nintendo Switch 2 Pro（VIIPER 原生）": "nintendo",
}

SPECIAL_ACTION_LABELS = {
    "禁用": "disabled",
    "F12": "key_f12",
    "F13": "key_f13",
    "F14": "key_f14",
    "Shift+Tab": "key_shift_tab",
    "Xbox Guide": "xinput_guide",
    "LB": "xinput_lb",
    "RB": "xinput_rb",
    "左摇杆按下": "xinput_l3",
    "右摇杆按下": "xinput_r3",
    "View/Back": "xinput_view",
    "Menu/Start": "xinput_menu",
}
ACTION_TO_LABEL = {value: key for key, value in SPECIAL_ACTION_LABELS.items()}

XBOX_HAPTIC_LABELS = {
    "HD2 均衡（推荐，最高 49%）": "balanced",
    "HD2 强劲（最高 78%）": "strong",
    "关闭震动": None,
}
NINTENDO_HAPTIC_LABELS = {
    "原生 HD Rumble 2 左/右直通": "native",
    "关闭震动": None,
}

STATE_LABELS = {
    "stopped": "已释放（可连接 NS2）",
    "scanning": "正在扫描（请按住 SYNC）",
    "connecting": "正在建立连接",
    "connected": "已连接，可进入 Steam",
}
STATE_COLORS = {
    "stopped": "#8b949e",
    "scanning": "#d29922",
    "connecting": "#d29922",
    "connected": "#2ea043",
}


class BridgeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"NS2 Pro 无线桥接 v{__version__}")
        self.geometry("780x650")
        self.minsize(720, 570)

        self._events: queue.Queue[tuple[str, object]] = queue.Queue()
        self._worker: BridgeWorker | None = None
        self._state = "stopped"
        self._last_packet_count = 0
        self._tray_icon = None
        self._hidden_to_tray = False
        self._exiting = False

        self.columnconfigure(0, weight=1)
        self.rowconfigure(6, weight=1)

        heading = ttk.Label(
            self,
            text=f"Nintendo Switch 2 Pro → Steam  ·  v{__version__}",
            font=("Segoe UI", 18, "bold"),
        )
        heading.grid(row=0, column=0, sticky="w", padx=18, pady=(16, 4))

        hint = ttk.Label(
            self,
            text=(
                "双端切换模式不会覆盖手柄的 NS2 配对记录。连接电脑时长按 SYNC；"
                "切回主机时点击“释放给 NS2”，再按手柄 HOME/A。"
            ),
            wraplength=630,
        )
        hint.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))

        control = ttk.Frame(self)
        control.grid(row=2, column=0, sticky="ew", padx=18)
        control.columnconfigure(5, weight=1)

        ttk.Label(control, text="虚拟设备：").grid(row=0, column=0, padx=(0, 6), pady=(0, 6))
        self._output = ttk.Combobox(
            control,
            state="readonly",
            width=34,
            values=tuple(OUTPUT_LABELS),
        )
        self._output.current(0)
        self._output.grid(row=0, column=1, padx=(0, 12), pady=(0, 6))
        self._output.bind("<<ComboboxSelected>>", self._on_output_changed)

        ttk.Label(control, text="按键映射：").grid(row=1, column=0, padx=(0, 6))
        self._layout = ttk.Combobox(
            control,
            state="readonly",
            width=22,
            values=("任天堂字母（A=A）", "Xbox 位置（底部=A）"),
        )
        self._layout.current(0)
        self._layout.grid(row=1, column=1, padx=(0, 12))

        self._connect_button = ttk.Button(control, text="连接电脑", command=self._connect)
        self._connect_button.grid(row=0, column=2, rowspan=2, padx=4)
        self._disconnect_button = ttk.Button(
            control, text="释放给 NS2", command=self._disconnect, state="disabled"
        )
        self._disconnect_button.grid(row=0, column=3, rowspan=2, padx=4)
        self._runtime_button = ttk.Button(control, text="ViGEmBus", command=self._open_runtime_help)
        self._runtime_button.grid(row=0, column=4, rowspan=2, padx=(12, 0))

        self._special_frame = ttk.LabelFrame(self, text="特殊按键（Xbox 模式可独立修改）")
        self._special_frame.grid(row=3, column=0, sticky="ew", padx=18, pady=(12, 0))
        self._special_boxes: dict[str, ttk.Combobox] = {}
        for column, (button, label) in enumerate(
            (("capture", "截图"), ("c", "C"), ("gl", "GL"), ("gr", "GR"))
        ):
            group = ttk.Frame(self._special_frame)
            group.grid(row=0, column=column, padx=8, pady=8, sticky="w")
            ttk.Label(group, text=f"{label} →").pack(side="left", padx=(0, 4))
            box = ttk.Combobox(
                group,
                state="readonly",
                width=13,
                values=tuple(SPECIAL_ACTION_LABELS),
            )
            default_action = DEFAULT_SPECIAL_MAPPINGS[button]
            box.set(ACTION_TO_LABEL[default_action])
            box.pack(side="left")
            self._special_boxes[button] = box

        haptic = ttk.Frame(self)
        haptic.grid(row=4, column=0, sticky="ew", padx=18, pady=(10, 0))
        ttk.Label(haptic, text="震动输出：").pack(side="left")
        self._haptic = ttk.Combobox(
            haptic,
            state="readonly",
            width=28,
            values=tuple(XBOX_HAPTIC_LABELS),
        )
        self._haptic.current(0)
        self._haptic.pack(side="left", padx=(4, 10))
        self._haptic_hint = ttk.Label(
            haptic,
            text="XInput 双频反馈 → HD Rumble 2；并非游戏原生波形透传",
            foreground="#666666",
        )
        self._haptic_hint.pack(side="left")

        status = ttk.Frame(self)
        status.grid(row=5, column=0, sticky="ew", padx=18, pady=14)
        self._dot = tk.Canvas(status, width=16, height=16, highlightthickness=0)
        self._dot_id = self._dot.create_oval(3, 3, 13, 13, fill=STATE_COLORS["stopped"], outline="")
        self._dot.pack(side="left")
        self._status_label = ttk.Label(status, text=STATE_LABELS["stopped"], font=("Segoe UI", 11, "bold"))
        self._status_label.pack(side="left", padx=(4, 12))
        self._rate_label = ttk.Label(status, text="")
        self._rate_label.pack(side="left")

        self._log = ScrolledText(
            self,
            height=15,
            state="disabled",
            font=("Consolas", 9),
            background="#0d1117",
            foreground="#c9d1d9",
            insertbackground="#c9d1d9",
            borderwidth=0,
        )
        self._log.grid(row=6, column=0, sticky="nsew", padx=18, pady=(0, 12))

        self._footer = ttk.Label(
            self,
            text="限制：ZL/ZR 为数字扳机；XInput 不传输陀螺仪，也不提供原生触觉波形。",
            foreground="#666666",
        )
        self._footer.grid(row=7, column=0, sticky="w", padx=18, pady=(0, 12))

        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Unmap>", self._on_unmap)
        self.after(100, self._poll_events)
        self.after(1000, self._poll_rate)
        self.after(250, self._watch_window_state)
        self._append_log("准备就绪。电脑连接为临时 GATT 会话，不会写入或覆盖 NS2 配对密钥。")
        self._append_log("连接电脑前请让 NS2 休眠；切回 NS2 时先点“释放给 NS2”。")
        self._refresh_output_controls()

        if sys.platform != "win32":
            self.after(0, lambda: messagebox.showerror("不支持的平台", "此程序仅支持 Windows 10/11。"))

    def _connect(self) -> None:
        if self._worker is not None and self._worker.running:
            return
        output_mode = OUTPUT_LABELS[self._output.get()]
        layout = "nintendo" if self._layout.current() == 0 else "xbox"
        special_mappings = {
            button: SPECIAL_ACTION_LABELS[box.get()]
            for button, box in self._special_boxes.items()
        }
        haptic_labels = (
            NINTENDO_HAPTIC_LABELS if output_mode == "nintendo" else XBOX_HAPTIC_LABELS
        )
        haptic_profile = haptic_labels[self._haptic.get()]
        self._worker = BridgeWorker(
            lambda kind, value: self._events.put((kind, value)),
            face_layout=layout,
            special_mappings=special_mappings,
            haptic_profile=haptic_profile,
            output_mode=output_mode,
        )
        self._worker.start()
        self._connect_button.configure(state="disabled")
        self._disconnect_button.configure(state="normal")
        self._layout.configure(state="disabled")
        self._output.configure(state="disabled")
        self._haptic.configure(state="disabled")
        for box in self._special_boxes.values():
            box.configure(state="disabled")

    def _disconnect(self) -> None:
        if self._worker is not None:
            self._worker.stop()
            self._append_log("正在释放 PC 连接；随后按手柄 HOME 或 A 即可返回 NS2。")
        self._disconnect_button.configure(state="disabled")

    def _set_state(self, state: str, detail: str = "") -> None:
        self._state = state
        self._dot.itemconfigure(self._dot_id, fill=STATE_COLORS.get(state, "#8b949e"))
        label = STATE_LABELS.get(state, state)
        if detail and state in {"connecting", "connected"}:
            label = f"{label} · {detail}"
        self._status_label.configure(text=label)
        if self._tray_icon is not None:
            self._tray_icon.title = f"NS2 Pro 无线桥接 v{__version__} - {label}"
        if state == "stopped":
            self._connect_button.configure(state="normal")
            self._disconnect_button.configure(state="disabled")
            self._layout.configure(state="readonly")
            self._output.configure(state="readonly")
            self._haptic.configure(state="readonly")
            for box in self._special_boxes.values():
                box.configure(state="readonly")
            self._rate_label.configure(text="")
            self._worker = None
            self._refresh_output_controls()

    def _on_output_changed(self, _event=None) -> None:
        self._refresh_output_controls()

    def _refresh_output_controls(self) -> None:
        if self._worker is not None and self._worker.running:
            return
        native = OUTPUT_LABELS[self._output.get()] == "nintendo"
        if native:
            self._layout.configure(state="disabled")
            for box in self._special_boxes.values():
                box.configure(state="disabled")
            self._haptic.configure(values=tuple(NINTENDO_HAPTIC_LABELS), state="readonly")
            self._haptic.current(0)
            self._haptic_hint.configure(text="Steam/SDL 原始 Nintendo 输出报告 → BLE 原生波形")
            self._runtime_button.configure(text="VIIPER/USBIP")
            self._footer.configure(
                text="Nintendo 模式原生输出 C/截图/GL/GR；需要 VIIPER Haptic v0.8.0 与 USBIP 驱动。"
            )
        else:
            self._layout.configure(state="readonly")
            for box in self._special_boxes.values():
                box.configure(state="readonly")
            self._haptic.configure(values=tuple(XBOX_HAPTIC_LABELS), state="readonly")
            self._haptic.current(0)
            self._haptic_hint.configure(text="XInput 双频反馈 → HD Rumble 2；并非游戏原生波形透传")
            self._runtime_button.configure(text="ViGEmBus")
            self._footer.configure(
                text="限制：ZL/ZR 为数字扳机；XInput 不传输陀螺仪，也不提供原生触觉波形。"
            )

    def _open_runtime_help(self) -> None:
        url = VIIPER_URL if OUTPUT_LABELS[self._output.get()] == "nintendo" else VIGEM_URL
        webbrowser.open(url)

    def _append_log(self, text: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", text + os.linesep)
        self._log.see("end")
        self._log.configure(state="disabled")

    def _poll_events(self) -> None:
        try:
            while True:
                kind, value = self._events.get_nowait()
                if kind == "log":
                    self._append_log(str(value))
                elif kind == "state":
                    state, detail = value
                    self._set_state(state, detail)
                elif kind == "error":
                    self._append_log(f"错误：{value}")
                    messagebox.showerror("NS2 Pro 无线桥接", str(value))
                elif kind == "tray":
                    if value == "show":
                        self._show_from_tray()
                    elif value == "disconnect":
                        self._disconnect()
                    elif value == "exit":
                        self._quit_application()
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _poll_rate(self) -> None:
        if self._worker is not None and self._state == "connected":
            current = self._worker.packet_count
            self._rate_label.configure(text=f"{current - self._last_packet_count} 包/秒")
            self._last_packet_count = current
        self.after(1000, self._poll_rate)

    @staticmethod
    def _tray_image():
        from PIL import Image, ImageDraw

        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((5, 12, 59, 52), radius=15, fill="#24292f")
        draw.ellipse((11, 22, 27, 38), outline="#ffffff", width=4)
        draw.line((19, 19, 19, 41), fill="#ffffff", width=4)
        draw.ellipse((39, 20, 47, 28), fill="#2ea043")
        draw.ellipse((47, 28, 55, 36), fill="#58a6ff")
        return image

    def _ensure_tray_icon(self) -> bool:
        if self._tray_icon is not None:
            return True
        try:
            import pystray
            def send(action: str) -> None:
                self._events.put(("tray", action))

            menu = pystray.Menu(
                pystray.MenuItem(
                    "显示主窗口", lambda _icon, _item: send("show"), default=True
                ),
                pystray.MenuItem(
                    "释放给 NS2",
                    lambda _icon, _item: send("disconnect"),
                    enabled=lambda _item: (
                        self._worker is not None and self._worker.running
                    ),
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("完全退出", lambda _icon, _item: send("exit")),
            )
            self._tray_icon = pystray.Icon(
                f"NS2ProBridge-v{__version__}",
                self._tray_image(),
                (
                    f"NS2 Pro 无线桥接 v{__version__} - "
                    f"{STATE_LABELS.get(self._state, self._state)}"
                ),
                menu,
            )
            self._tray_icon.run_detached()
        except Exception as exc:
            self._tray_icon = None
            self._append_log(
                f"系统托盘初始化失败（{type(exc).__name__}: {exc}）；"
                "窗口将仅最小化到任务栏。"
            )
            return False
        return True

    def _hide_to_tray(self) -> None:
        if self._hidden_to_tray or self._exiting:
            return
        if not self._ensure_tray_icon():
            self.iconify()
            return
        self._hidden_to_tray = True
        self.withdraw()
        self._append_log("主窗口已隐藏到系统托盘；桥接继续在后台运行。")
        try:
            self._tray_icon.notify(
                "桥接仍在后台运行。双击托盘图标可恢复窗口。",
                f"NS2 Pro 无线桥接 v{__version__}",
            )
        except (NotImplementedError, OSError):
            pass

    def _show_from_tray(self) -> None:
        self._hidden_to_tray = False
        self.deiconify()
        self.state("normal")
        self.lift()
        self.focus_force()

    def _on_unmap(self, event: tk.Event) -> None:
        if event.widget is not self or self._hidden_to_tray or self._exiting:
            return
        self.after_idle(self._minimize_to_tray_if_running)

    def _minimize_to_tray_if_running(self) -> None:
        if self._should_hide_to_tray(
            self.state(),
            self._worker is not None and self._worker.running,
            self._hidden_to_tray,
            self._exiting,
        ):
            self._hide_to_tray()

    @staticmethod
    def _should_hide_to_tray(
        window_state: str,
        bridge_running: bool,
        already_hidden: bool,
        exiting: bool,
    ) -> bool:
        return (
            window_state == "iconic"
            and bridge_running
            and not already_hidden
            and not exiting
        )

    def _watch_window_state(self) -> None:
        """Catch Windows/Tk minimize transitions that do not emit a timely Unmap."""
        if not self._exiting:
            self._minimize_to_tray_if_running()
            self.after(250, self._watch_window_state)

    def _close(self) -> None:
        if self._worker is not None and self._worker.running and not self._exiting:
            self._hide_to_tray()
            return
        self._quit_application()

    def _quit_application(self) -> None:
        if self._exiting:
            return
        self._exiting = True
        if self._worker is not None:
            self._worker.stop()
        self._finish_exit(time.monotonic() + 3.0)

    def _finish_exit(self, deadline: float) -> None:
        if self._worker is not None and self._worker.running and time.monotonic() < deadline:
            self.after(100, lambda: self._finish_exit(deadline))
            return
        if self._tray_icon is not None:
            self._tray_icon.stop()
            self._tray_icon = None
        self.destroy()


def main() -> None:
    BridgeApp().mainloop()


if __name__ == "__main__":
    main()
