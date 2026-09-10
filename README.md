# NS2 Pro 无线桥接

当前版本：**v0.5.1** · [更新日志](CHANGELOG.md) · [发布流程](RELEASING.md)

让 Nintendo Switch 2 Pro Controller 在 Windows 11 上通过蓝牙连接，并可选择向 Steam/PC 游戏提供虚拟 Xbox 360 手柄，或真正以 USB `VID 057E / PID 2069` 的 Nintendo Switch 2 Pro Controller 身份出现。

Windows 的“添加蓝牙设备”看不到它是正常现象：手柄使用 Bluetooth LE 私有 GATT 协议，广播中没有普通设备名称。本程序直接扫描 Nintendo 厂商数据、连接手柄并翻译输入，不需要先在 Windows 设置中配对，也不需要 Switch 2 主机。

## 当前功能

- 只匹配 Nintendo 厂商 ID `0x0553` 和 Switch 2 Pro PID `0x2069`，不会误连附近的 Joy-Con 2。
- 支持蓝牙扫描、连接、断线后重新扫描。
- 连接或扫描期间，点击最小化或窗口关闭按钮会隐藏到系统托盘，桥接继续在后台运行；托盘菜单可恢复窗口、释放给 NS2 或完全退出。
- 采用非持久 GATT 会话，不写电脑地址或配对密钥，保留手柄原有的 NS2 配对记录。
- 支持 A/B/X/Y、方向键、L/R、ZL/ZR、+/−、HOME、L3/R3 和双摇杆。
- 支持 C、截图、GL、GR，四者都可单独映射为 F12/F13/F14、Shift+Tab 或现有 XInput 按钮。
- 通过 ViGEmBus 输出虚拟 Xbox 360 手柄，可用于 Steam 和普通 XInput 游戏。
- 可选的“VIIPER 原生”模式通过 USBIP 输出 Nintendo Switch 2 Pro 身份，原生保留 C、截图、GL、GR，并接收 Steam/SDL 的左右 HD Rumble 2 输出。
- 默认“任天堂字母”映射：实体 A 输出逻辑 A、实体 B 输出逻辑 B；也可切换为 Xbox 按键位置。
- 接收游戏的 XInput 双马达反馈，并转换为 Switch 2 Pro 的五字节 HD Rumble 2 低/高频帧；BLE 端按 15 ms 最新值优先发送并在断开时发送停止帧。

ZL/ZR 是数字扳机，这与手柄硬件一致。当前不输出陀螺仪、耳机和 NFC。

### 两种输出与震动能力边界

默认的“HD2 均衡”是兼容性方案：Xbox 360/XInput 只向程序提供一个低频（large）和一个高频（small）强度，程序将它们合成为 HD Rumble 2 帧并同时送往手柄左右执行器。它保留强弱和低/高频差异，但不是游戏原始的 Nintendo HD Rumble 2 波形，也没有左右位置数据。默认最大协议幅度为 500/1023；“强劲”档为 800/1023，若听到明显敲击声应改回均衡。

“VIIPER 原生”模式已实现这条路线：内置的独立 VIIPER Haptic v0.8.0 进程创建 Switch 2 Pro USB 身份，程序把其左右各 16 字节 HID 波形转换为实体 Pro2 的 33 字节 `CC48…` BLE 帧。它最接近原生 HD Rumble 2，但最终效果仍取决于 Steam/SDL 或游戏是否实际向 Nintendo 设备发送原始输出报告；NFC、耳机和蓝牙身份不在模拟范围。

## 安装

要求：Windows 10/11、支持 BLE 的蓝牙适配器、Python 3.10+（直接使用打包 EXE 时不需要 Python）。

1. Xbox 模式：安装 [ViGEmBus 1.22.0](https://github.com/nefarius/ViGEmBus/releases/tag/v1.22.0)，然后重启电脑。
2. Nintendo 模式：安装 USBIP 驱动并重启。VIIPER 文档警告旧 usbip-win2 安装包会加入公开测试签名根证书；建议优先阅读 [VIIPER USBIP 安全说明](https://github.com/Alia5/VIIPER/blob/main/docs/getting-started/usbip.md)并考虑 OSSign 的已修复预发布驱动。程序不会自动安装驱动。
3. 在 PowerShell 中进入项目目录并运行：

   ```powershell
   .\scripts\setup.ps1
   ```

4. 启动程序：

   ```powershell
   .\scripts\run.ps1
   ```

也可以执行 `.\scripts\build.ps1`，生成带版本号的 `dist\vX.Y.Z\NS2ProBridge-vX.Y.Z.exe`。窗口标题、文件名和 Windows 文件属性会显示同一版本，避免误启旧版。

## 使用

1. 不要在 Windows“添加蓝牙设备”中配对。如果以前添加过相关设备，请先移除。
2. 关闭 Switch 2 主机或让手柄远离主机，并拔掉手柄 USB 线。
3. 打开程序，保留默认的“任天堂字母（A=A）”，点击“连接电脑”。
4. 持续按住手柄顶部 USB-C 接口旁的 SYNC 键，直到程序状态变绿。
5. Steam 应显示一个 Xbox 360 Controller。支持 XInput 的游戏通常无需 Steam Input；若使用 Steam 自定义布局，则为 Xbox 控制器启用 Steam Input。不要启用“使用任天堂按键布局”再次交换字母。

连接后可点击最小化或右上角关闭：窗口会隐藏到通知区域，手柄不会断开。双击托盘图标恢复窗口；右键菜单中的“完全退出”才会停止桥接并关闭程序。

若选择“ Nintendo Switch 2 Pro（VIIPER 原生）”，Steam 应看到 Nintendo Switch 2 Pro Controller；此时建议为它启用 Steam Input，以便 Steam/SDL 处理 C、截图、GL/GR 和 Nintendo 原始震动输出。游戏若原生支持该设备，也可按游戏情况关闭 Steam Input 对比测试。

默认特殊键映射：

- 截图 → `F12`（Steam 默认截图键）
- C → `Shift+Tab`（Steam 默认界面快捷键）
- GL → `F13`
- GR → `F14`

GL/GR 使用 F13/F14 时保持为两个独立输入，可在支持键盘绑定的游戏里设置。也可在连接前把它们改成 LB/RB/L3/R3 等 XInput 按钮；这种映射会和原按钮共享同一个逻辑输入。

### 在电脑和 NS2 之间切换

- **NS2 → 电脑：** 让 NS2 休眠或关闭，打开本程序并点击“连接电脑”，持续按住 SYNC，直到状态变绿。
- **电脑 → NS2：** 在本程序点击“释放给 NS2”，等待状态显示“已释放”，然后按手柄 HOME 或 A。手柄会使用原先保存的 NS2 配对记录重新连接主机。
- PC 端是临时直连，不调用 Windows 配对，也不向手柄写入新的主机地址或配对密钥。因此正常切换不需要在 NS2 上反复注册手柄。

这不是无感双主机切换：回到电脑时仍需要长按 SYNC，因为电脑没有被保存成第二个配对槽。这样做是为了避免覆盖唯一的 NS2 主机配对记录。

程序已经完成字母映射，不要再在 Steam 中额外交换 A/B、X/Y，否则会发生双重交换。由于 Steam 看到的是 Xbox 手柄，部分游戏仍会显示 Xbox 风格图标。

## 故障排查

- **扫描不到：** 确认 Windows 蓝牙已开启、USB 已拔掉，按住而不是点按 SYNC。连续失败后等待约两分钟再试，手柄固件可能有连接冷却。
- **“设备未就绪” (`0x800710DF`)：** 这是 Windows 在 BLE 扫描开始前返回的射频错误。关闭“添加设备”弹窗，将系统蓝牙开关关闭再打开；仍失败则重启电脑。程序会先读取实际射频状态并给出对应提示。
- **“操作已被用户取消” (`0x800704C7`)：** 这通常是 Windows 配对/许可流程取消了 GATT，并不代表你点了取消。关闭“添加设备”和所有系统配对通知；在 Windows 已保存的设备中移除旧的 Nintendo/Pro Controller 条目；让 NS2 休眠，持续按住 SYNC。程序会显示具体失败阶段，按广播携带的 public/random 地址类型并使用未缓存服务自动重试。
- **发现后连接失败：** 保持 SYNC 状态让程序重试；Windows 第一次建立 GATT 服务可能需要数次尝试。
- **无法创建虚拟手柄：** 安装/修复 ViGEmBus 1.22.0 并重启电脑。
- **游戏出现双重输入：** 关闭 BetterJoy、reWASD、JoyShockMapper 等其他映射工具。
- **游戏没有震动：** 确认程序中未选择“关闭震动”，游戏自身已开启震动，并避免让其他映射程序抢占虚拟手柄。Steam“控制器测试”不一定主动发送持续震动，最好用已知支持 XInput 震动的游戏验证。
- **震动过强或有敲击声：** 改用“HD2 均衡”，或暂时关闭震动。强劲档只用于按个人手柄情况测试。
- **F12/F13/F14 没反应：** 以管理员身份运行的游戏可能不会接收普通权限程序注入的按键；让桥接器和游戏处于相同权限级别，或把特殊键改映射为 XInput 按钮。
- **切不回 NS2：** 确认程序已显示“已释放”，关闭 PC 端其他手柄工具，再按 HOME/A；通常不需要在主机上重新注册。
- **按键字母相反：** 在本程序选择正确布局，并取消 Steam 或游戏内的额外 A/B、X/Y 交换。

## 开发与测试

协议解析测试不需要真实手柄：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

版本变更记录见 [`CHANGELOG.md`](CHANGELOG.md)，发布步骤见 [`RELEASING.md`](RELEASING.md)。推送 `v*` Git 标签后，GitHub Actions 会测试、构建 Windows EXE 并创建对应 Release。

`vendor/vgamepad-0.1.0-py3-none-any.whl` 是从官方 MIT 源码包构建的固定 CI 依赖。PyPI 的源码包在生成元数据时会尝试启动交互式 ViGEmBus MSI，无法用于无人值守 Runner；预装 wheel 只跳过该安装副作用，最终 EXE 仍要求用户自行安装 ViGEmBus。

架构：

```text
Switch 2 Pro BLE 广播/GATT（不配对，保留 NS2 记录）
        ↓
bleak 扫描与通知
        ↓
protocol.py 解码按钮和摇杆
        ├─ vgamepad + ViGEmBus ↔ Xbox 360 / XInput ↔ HD2 合成
        └─ VIIPER + USBIP ↔ Nintendo 057E:2069 ↔ 原始 HID 波形转换
                                                    ↓
                                           CC48 原始震动 GATT
```

## 来源与许可

本项目采用 MIT 许可。BLE 广播格式、GATT UUID、初始化命令与输入报告布局参考了以下开源成果：

- [Switch2BTLink](https://github.com/KumuIi/Switch2BTLink)（MIT）
- [joycon2cpp](https://github.com/TheFrano/joycon2cpp)（MIT）
- [XinHeLianSheng Pro2 Bridge](https://github.com/LeonChrome/XinHeLianSheng-Pro2-Bridge)（Apache-2.0，虚拟设备/震动路线架构参考）
- [S2P-XInput-Lite](https://github.com/duoduo-88/S2P-XInput-Lite)（GPL-3.0，公开协议说明与 BLE 节奏对照；本项目未复制其 GPL 源码）

完整署名见 `THIRD_PARTY_NOTICES.md`。
