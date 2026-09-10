# 发布新版本

1. 在 `src/ns2pro_bridge/__init__.py` 更新 `__version__`，采用 `MAJOR.MINOR.PATCH`。
2. 在 `CHANGELOG.md` 顶部记录新增、变更和修复内容及日期。
3. 核对 `THIRD_PARTY_NOTICES.md` 与 `LEGAL.md`，确认所有随包二进制的许可证和对应源码仍完整。
4. 运行 `./scripts/setup.ps1`、`./.venv/Scripts/python.exe -m pytest` 和 `./scripts/build.ps1`。
5. 提交全部源码变更，创建与版本一致的标签，例如 `git tag -a v0.6.0 -m "Release v0.6.0"`。
6. 推送提交和标签。GitHub Actions 会测试、构建、校验 GPL 对应源码、生成来源证明并创建 Release。

不要提交 `dist/`、`build/`、虚拟环境或测试缓存。发布产物由工作流生成并附加到 GitHub Release。
