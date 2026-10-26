# 日常学习 · Daily Study

一个按学习目标组织资料、阅读、AI问答与复习的桌面应用。原生窗口与系统WebView，随包附带Python后端；用户无需安装Node/Python。

[下载最新版本](https://github.com/frostloom/study/releases/latest) · [安装与开发说明](docs/usage.md)

- 自由填写目标与基础，AI检索真实公开资料，预览后选择加入阅读；支持MD/TXT/HTML/PDF/DOCX。
- 阅读时选中文字划重点、写批注或问AI；按当前小节提供上下文，保留分会话历史。
- 每日学习与复习按时间预算安排，真实勾选和回答保留历史；长篇可分段学习。
- 白色、黑色与护眼纸色。新版本发布后自动检查，左下角自动显示更新提示。
- 正式版与开发预览独立数据和窗口身份，迭代不会污染日常学习。

## 安装

macOS13+：AppleSilicon选择macos-arm64，Intel选择macos-x64，打开DMG并将应用拖入Applications。Windows10/11x64：选择windows-x64-setup.exe安装，或解压ZIP使用；需要系统WebView2运行时。

当前Mac临时签名、未Apple公证，Windows未配置发行者签名证书；系统可能显示发行者提示。首次设置需自己的OpenAI兼容ChatCompletions模型服务。模型密钥和学习资料仅存于用户数据目录，不在仓库/发行包内；调用AI时选定的学习上下文会发送给配置的模型服务。

## 开发

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
# Mac: 构建一次原生预览外壳
BUILD_PYTHON="$PWD/.venv/bin/python" BUILD_CHANNEL=preview BUILD_DIST="$PWD/release-preview" tools/build_macos.sh
.venv/bin/python tools/preview.py
```

预览窗口使用当前源码后端：改前端后CmdR刷新；改Python后退出并重新启动预览。预览不自动导入正式资料或运行正式学习定时器。Windows用tools/build_windows.ps1 -Channel preview构建，再运行python tools/preview.py。

测试：`python tools/ci_tests.py`；`node docs/frontend-update-test.cjs`及其余frontend行为脚本。正式构建：Mac tools/build_macos.sh，Windows tools/build_windows.ps1。推送vX.Y.Z标签且版本与app_info.py一致后，GitHubActions在三种架构运行完整测试、冻结包和原生烟测，再统一发布Release与SHA256。应用启动后自动检查stable/latest，运行期间每6小时检查，不提示安装草稿/预发布。

正式数据：Mac ~/Library/Application Support/日常学习；Windows %LOCALAPPDATA%/DailyStudy。应用升级不替换数据目录。预览分别用日常学习预览版 / DailyStudy Preview。
