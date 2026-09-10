# 发布新版本

1. 在 `src/ns2pro_bridge/__init__.py` 更新 `__version__`，采用 `MAJOR.MINOR.PATCH`。
2. 在 `CHANGELOG.md` 顶部记录新增、变更和修复内容及日期。
3. 运行 `./scripts/setup.ps1`、`./.venv/Scripts/python.exe -m pytest` 和 `./scripts/build.ps1`。
4. 提交全部源码变更，创建与版本一致的标签，例如 `git tag -a v0.5.0 -m "Release v0.5.0"`。
5. 推送提交和标签。GitHub Actions 会重新测试、构建带版本号的 EXE，并创建 Release。

不要提交 `dist/`、`build/`、虚拟环境或测试缓存。发布产物由工作流生成并附加到 GitHub Release。
