# 兼容范围

“在任何 Windows 11 PC 上支持任何官方手柄”不是可以诚实验证的绝对承诺。没有 BLE 硬件、禁止第三方驱动的企业电脑、Windows S 模式、ARM64 驱动组合以及 Nintendo 未来改变的固件协议都可能超出程序控制范围。本项目采用下面可测试、可维护的支持边界。

## 正式支持

| 项目 | 支持范围 |
|---|---|
| 手柄 | Nintendo 官方 Switch 2 Pro Controller；Nintendo 厂商 ID `0x0553`、产品 ID `0x2069` |
| 地区 | 不检查销售地区；日、美、欧等使用相同广播身份与报告格式的官方产品走同一代码路径 |
| 固件 | 使用当前公开逆向协议、已完成 Switch 2 初始化且仍广播 PID `0x2069` 的固件 |
| PC | Windows 11 x64 桌面版，具有可用的 Bluetooth Low Energy 适配器 |
| Xbox 模式 | ViGEmBus 1.22.0；普通 XInput/Steam 游戏 |
| Nintendo 模式 | x64 USBIP-Win2 0.9.7.7 + 内置 VIIPER Haptic；Steam/SDL 是否提供特殊键与原始震动取决于其版本和游戏 |

程序不会因销售地区或 Windows 地区设置拒绝手柄。v0.6.0 起，Nintendo 广播的格式修订字节可以变化，只要厂商、框架前缀和产品 ID 仍匹配。发现未知 Nintendo 广播时，程序会把去身份化的厂商数据写入日志，便于通过问题模板增加适配。

## 尚未保证

- Windows 11 ARM64：ViGEmBus 上游包含 ARM64 驱动，但本项目的 EXE、vgamepad 客户端和 USBIP 组合尚未完成端到端硬件测试。
- Windows S 模式、Windows Server、虚拟机、远程桌面会话以及禁止驱动安装的受管电脑。
- 没有 BLE、蓝牙被 BIOS/策略禁用或只支持传统蓝牙的电脑。
- Nintendo 未来硬件修订、未来改变 GATT UUID/初始化命令/报告布局的固件。
- 第三方、仿制或改装手柄，即使它们冒用相同名称或 VID/PID。
- NFC、耳机、麦克风、唤醒电脑和陀螺仪输出。
- 每一款游戏的图标、Steam Input 策略和震动波形；Xbox 模式只能合成震动，Nintendo 模式仍取决于游戏实际发送的报告。

## 发布验收

每个版本必须通过协议、按键、震动、Nintendo 虚拟设备和托盘回归测试；GitHub Windows Runner 必须成功生成带版本号的 EXE。真实手柄、蓝牙芯片和驱动组合无法由云 Runner 模拟，因此兼容性报告必须注明 Windows 构建、架构、蓝牙适配器、手柄固件/地区和输出模式。
