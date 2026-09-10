# 更新日志

本项目遵循[语义化版本](https://semver.org/lang/zh-CN/)，所有正式版本均使用 Git 标签保存。

## [0.6.0] - 2026-09-10

### 新增

- 增加公开发布前的权利、许可、安全和兼容范围文档。
- Release 随附 VIIPER 精确对应源码归档，并为 EXE 生成 GitHub 构建来源证明。
- 增加 Dependabot 和结构化兼容性问题模板。
- 记录未识别 Nintendo BLE 广播，便于适配未来官方固件。

### 变更

- 广播识别允许官方格式修订字节变化，同时继续严格限定 Nintendo 厂商 ID 与 Pro2 PID。
- 系统托盘改用 Windows Shell 原生 API，移除 Pillow 和 LGPL pystray 依赖。
- CI 从固定 SHA-256 的 vgamepad 0.1.0 上游源码即时构建 wheel，并以可审计补丁禁用旧驱动 MSI；不再提交预构建 wheel。
- 发布 EXE 只收集运行所需的 x64 ViGEmClient DLL，明确拒绝打包上游旧版驱动 MSI 和无关的 x86 客户端。

[0.6.0]: https://github.com/TohruUehera/NS2Pro-Bridge-Windows/compare/v0.5.1...v0.6.0

## [0.5.1] - 2026-09-10

### 修复

- 固定 vgamepad wheel，防止无人值守 Runner 被其交互式驱动安装过程阻塞。
- 为 GitHub Windows 构建设置明确的超时时间，使失败可以被追踪和诊断。

## [0.5.0] - 2026-09-10

### 新增

- 窗口标题、主界面、EXE 文件名和 Windows 文件属性统一显示版本号。
- 加入 GitHub Actions：测试通过后构建 Windows EXE；推送 `v*` 标签时生成 GitHub Release。

### 修复

- 使用周期性窗口状态检测补强 Windows/Tk 的最小化事件，避免偶发无法隐藏到托盘。
- 防止重复触发隐藏事件或退出期间重新创建托盘图标。

## [0.4.0] - 2026-09-06

### 新增

- 连接或扫描期间关闭、最小化到系统托盘。
- 托盘菜单可恢复窗口、释放手柄给 NS2 或完全退出。

## [0.3.0] - 2026-09-06

### 新增

- Nintendo `057E:2069` 虚拟设备模式和 VIIPER/USBIP 集成。
- C、截图、GL、GR 原生输出与 HD Rumble 2 波形转换。
- 保留 NS2 配对记录的 BLE 临时连接方案。

[0.5.1]: https://github.com/TohruUehera/NS2Pro-Bridge-Windows/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/TohruUehera/NS2Pro-Bridge-Windows/releases/tag/v0.5.0
[0.4.0]: https://github.com/TohruUehera/NS2Pro-Bridge-Windows#历史版本说明
[0.3.0]: https://github.com/TohruUehera/NS2Pro-Bridge-Windows#历史版本说明
