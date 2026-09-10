# 安全策略

## 支持版本

只为最新正式 Release 提供安全修复。使用者应从本仓库 Releases 下载，并核对资产 SHA-256 或运行 GitHub artifact attestation 验证。

## 私下报告漏洞

请使用 GitHub 仓库的 **Security → Report a vulnerability** 私密报告功能。不要在公开 Issue 中提交配对密钥、账户令牌、完整设备标识或其他隐私数据。

## 驱动与权限

本程序不会自动安装驱动。ViGEmBus 与 USBIP 都是内核级组件，应只从文档列出的上游项目获取；安装需要管理员权限和重启。受管设备应先获得管理员批准。
