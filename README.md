# 日常学习 Desktop 1.0.0

轻量 macOS 学习应用：原生 AppKit/WKWebView 窗口，随包附带 Python 后端，用户不需要安装 Python、Node 或其他运行时。

首次打开按页面完成：兼容模型连接与验证 → 学习目标 → 基础与节奏 → 搜索、预览并选择资料 → 每天时间与自动安排 → 确认。没有固定学科列表。目标、资料、模型和时间之后均可在设置修改。

- 根据目标生成检索词，再对实际公开搜索结果排序。预览真实正文后确认加入阅读；不会把模型编造的链接当搜索结果。
- 支持 MD、TXT、HTML、PDF、DOCX 导入。单个8MB、每批最多6个、合计32MB；保留原文件。扫描PDF需要先识别文字。
- 阅读时可选中、高亮、批注、问AI；桌面AI半屏，手机全宽。仅提供当前小节和当前会话最近最多30轮/4万字符历史。
- 新对话不删除旧会话，历史可随时切回；等待中的回复归回原会话。
- 每天阅读/复习预算可调。长模块可以分段安排，完成一段不会假定读完整篇。
- 白色默认，黑色和纸色可选。没有口号或固定侧栏状态。
- 可跳过、可重播的操作引导。实际问答和勾选才进入学习记录，不伪造学习成绩。

## 使用与数据

打开“日常学习.app”。首次运行如发现 `~/日常学习` 的旧库，会安全复制到 `~/Library/Application Support/日常学习`；原件不删除。模型改为 OpenAI 兼容 Chat Completions 接口，需自行填写地址、模型名和密钥（本地服务可无密钥）并测试。没有本机账号或命令行模型集成。

关闭窗口后应用仍运行，Dock可重新打开；⌘Q完全退出。自动计划/复习需要应用运行、电脑唤醒。时间设置用于新计划，已保存的学习事实和当日计划保留。数据备份可在设置创建，备份不包含模型密钥。

当前构建适用于 Apple Silicon / macOS13+，采用临时签名，未经过Apple公证。正式公开分发前请完成DeveloperID签名与公证；步骤见 `docs/native-packaging.md`，脚本 `tools/notarize_macos.sh`。不建议关闭系统安全保护。

## 开发与构建

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python backend_entry.py --root /private/tmp/my-study-data --port 8765 --no-legacy
BUILD_PYTHON="$PWD/.venv/bin/python" tools/build_macos.sh
```

测试：`.venv/bin/python -m unittest discover -s tests -v`；前端行为测试：`node docs/frontend-contract-test.cjs`、`frontend-save-test.cjs`、`frontend-preview-test.cjs`、`frontend-tour-completion-test.cjs`。测试用途Node不是应用运行依赖。

第三方运行组件许可随应用发布；前端组件许可在 `static/vendor/`。原用户资料不会被打进发行包。
