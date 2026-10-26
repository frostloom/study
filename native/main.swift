import AppKit
import WebKit

final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate, WKNavigationDelegate, WKUIDelegate {
    #if PREVIEW
    let channel = "preview"
    let appName = "日常学习预览版"
    #else
    let channel = "stable"
    let appName = "日常学习"
    #endif
    var window: NSWindow!
    var web: WKWebView!
    var process: Process?
    var readyURL: URL?
    var generation = UUID()
    var startupText = ""
    var retryButton: NSButton!
    var statusLabel: NSTextField!
    var statusView: NSView!
    var dataRoot: URL {
        let args = CommandLine.arguments
        if let i = args.firstIndex(of: "--data-dir"), i + 1 < args.count {
            return URL(fileURLWithPath: args[i + 1], isDirectory: true)
        }
        return FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/" + appName, isDirectory: true)
    }
    func applicationDidFinishLaunching(_ notification: Notification) {
        makeMenu()
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1280, height: 840), styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        window.title = appName
        window.minSize = NSSize(width: 980, height: 700)
        window.delegate = self
        window.isReleasedWhenClosed = false
        window.center()
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()
        web = WKWebView(frame: .zero, configuration: config)
        web.navigationDelegate = self
        web.uiDelegate = self
        web.autoresizingMask = [.width, .height]
        window.contentView = web
        makeStatus()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        startBackend()
    }
    func makeStatus() {
        statusView = NSView(frame: web.bounds)
        statusView.autoresizingMask = [.width, .height]
        statusLabel = NSTextField(wrappingLabelWithString: "正在启动本地学习服务…")
        statusLabel.font = .systemFont(ofSize: 17)
        statusLabel.alignment = .center
        statusLabel.translatesAutoresizingMaskIntoConstraints = false
        retryButton = NSButton(title: "重试", target: self, action: #selector(retry))
        retryButton.translatesAutoresizingMaskIntoConstraints = false
        retryButton.isHidden = true
        statusView.addSubview(statusLabel)
        statusView.addSubview(retryButton)
        NSLayoutConstraint.activate([
            statusLabel.centerXAnchor.constraint(equalTo: statusView.centerXAnchor),
            statusLabel.centerYAnchor.constraint(equalTo: statusView.centerYAnchor, constant: -30),
            statusLabel.widthAnchor.constraint(lessThanOrEqualToConstant: 660),
            retryButton.topAnchor.constraint(equalTo: statusLabel.bottomAnchor, constant: 22),
            retryButton.centerXAnchor.constraint(equalTo: statusView.centerXAnchor)
        ])
        web.addSubview(statusView)
    }
    func fail(_ message: String) {
        statusLabel.stringValue = "学习服务启动失败\n\n" + message
        retryButton.isHidden = false
        statusView.isHidden = false
    }
    @objc func retry() { stopBackend(); startBackend() }
    func startBackend() {
        web.stopLoading()
        generation = UUID()
        let current = generation
        readyURL = nil
        startupText = ""
        statusLabel.stringValue = "正在启动本地学习服务…"
        retryButton.isHidden = true
        statusView.isHidden = false
        guard let resources = Bundle.main.resourceURL else { fail("无法找到应用资源。请重新安装应用。"); return }
        let child = Process()
        child.executableURL = resources.appendingPathComponent("backend/study-backend")
        var args = ["--root", dataRoot.path, "--port", "0", "--channel", channel, "--parent-pid", String(ProcessInfo.processInfo.processIdentifier)]
        #if PREVIEW
        let cli = CommandLine.arguments
        if let sourceIndex = cli.firstIndex(of: "--source-dir"), sourceIndex + 1 < cli.count,
           let pythonIndex = cli.firstIndex(of: "--python"), pythonIndex + 1 < cli.count {
            let source = URL(fileURLWithPath: cli[sourceIndex + 1]).appendingPathComponent("backend_entry.py")
            child.executableURL = URL(fileURLWithPath: cli[pythonIndex + 1])
            args = [source.path] + args
        }
        #endif
        if channel == "preview" || CommandLine.arguments.contains("--no-legacy") { args.append("--no-legacy") }
        else {
            let legacy = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("日常学习")
            if FileManager.default.fileExists(atPath: legacy.path) { args += ["--legacy-root", legacy.path] }
        }
        child.arguments = args
        var env = ProcessInfo.processInfo.environment
        env["PYTHONUNBUFFERED"] = "1"
        let ca = resources.appendingPathComponent("backend/_internal/certifi/cacert.pem").path
        env["SSL_CERT_FILE"] = ca
        env["REQUESTS_CA_BUNDLE"] = ca
        child.environment = env
        let output = Pipe(), errors = Pipe()
        child.standardOutput = output
        child.standardError = errors
        process = child
        errors.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            if data.isEmpty { handle.readabilityHandler = nil; return }
            let text = String(decoding: data, as: UTF8.self)
            DispatchQueue.main.async { if self?.generation == current { self?.startupText = String(((self?.startupText ?? "") + text).suffix(2500)) } }
        }
        child.terminationHandler = { [weak self] proc in
            DispatchQueue.main.async {
                guard let self = self, self.generation == current else { return }
                self.fail("服务已退出（状态 \(proc.terminationStatus)）。\n" + self.startupText)
            }
        }
        do { try child.run() } catch { fail(error.localizedDescription); return }
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            var line = Data()
            while line.count < 16384 {
                let part = output.fileHandleForReading.readData(ofLength: 1)
                if part.isEmpty { break }
                if part[0] == 10 { break }
                line.append(part)
            }
            DispatchQueue.main.async {
                guard let self = self, self.generation == current else { return }
                guard let json = try? JSONSerialization.jsonObject(with: line) as? [String: Any],
                      let value = json["url"] as? String, let url = URL(string: value),
                      url.scheme == "http", url.host == "127.0.0.1", let port = url.port, port > 0,
                      url.user == nil, url.password == nil else {
                    self.fail("服务没有返回有效的本地地址。\n" + self.startupText); return
                }
                self.readyURL = url
                self.web.load(URLRequest(url: url))
            }
            // Drain later backend output so a full pipe can never block the server.
            while !output.fileHandleForReading.readData(ofLength: 4096).isEmpty {}
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 30) { [weak self] in
            guard let self = self, self.generation == current, self.readyURL == nil else { return }
            self.stopBackend()
            self.fail("启动超过 30 秒。请重试，或检查数据目录的访问权限。\n" + self.startupText)
        }
    }
    func stopBackend() {
        generation = UUID()
        guard let child = process else { return }
        child.terminationHandler = nil
        if child.isRunning { child.terminate() }
        process = nil
    }
    func applicationWillTerminate(_ notification: Notification) { stopBackend() }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        window.makeKeyAndOrderFront(nil); return true
    }
    func sameOrigin(_ url: URL) -> Bool {
        guard let local = readyURL else { return false }
        return url.scheme == local.scheme && url.host == local.host && url.port == local.port && url.user == nil && url.password == nil
    }
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url else { decisionHandler(.cancel); return }
        if sameOrigin(url) { decisionHandler(.allow); return }
        if action.navigationType == .linkActivated && ["http", "https"].contains(url.scheme ?? "") { NSWorkspace.shared.open(url) }
        decisionHandler(.cancel)
    }
    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration, for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let url = action.request.url {
            if sameOrigin(url) { webView.load(URLRequest(url: url)) }
            else if ["http", "https"].contains(url.scheme ?? "") { NSWorkspace.shared.open(url) }
        }
        return nil
    }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        if let url = webView.url, sameOrigin(url) { statusView.isHidden = true }
    }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        if (error as NSError).code != NSURLErrorCancelled { fail(error.localizedDescription) }
    }
    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        if (error as NSError).code != NSURLErrorCancelled { fail(error.localizedDescription) }
    }
    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        fail("页面进程已停止。请重试以重新打开学习工作台。")
    }
    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
        guard let origin = frame.request.url, sameOrigin(origin) else { completionHandler(nil); return }
        let panel = NSOpenPanel()
        panel.canChooseDirectories = false
        panel.canChooseFiles = true
        panel.allowsMultipleSelection = parameters.allowsMultipleSelection
        panel.beginSheetModal(for: window) { response in completionHandler(response == .OK ? panel.urls : nil) }
    }
    func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
        guard let url = frame.request.url, sameOrigin(url) else { completionHandler(); return }
        let alert = NSAlert(); alert.messageText = "日常学习"; alert.informativeText = message
        alert.beginSheetModal(for: window) { _ in completionHandler() }
    }
    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        guard let url = frame.request.url, sameOrigin(url) else { completionHandler(false); return }
        let alert = NSAlert(); alert.messageText = "日常学习"; alert.informativeText = message
        alert.addButton(withTitle: "确定"); alert.addButton(withTitle: "取消")
        alert.beginSheetModal(for: window) { result in completionHandler(result == .alertFirstButtonReturn) }
    }
    func webView(_ webView: WKWebView, runJavaScriptTextInputPanelWithPrompt prompt: String, defaultText: String?, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (String?) -> Void) {
        guard let url = frame.request.url, sameOrigin(url) else { completionHandler(nil); return }
        let alert = NSAlert(); alert.messageText = "日常学习"; alert.informativeText = prompt
        let field = NSTextField(string: defaultText ?? ""); field.frame = NSRect(x: 0, y: 0, width: 320, height: 24)
        alert.accessoryView = field; alert.addButton(withTitle: "确定"); alert.addButton(withTitle: "取消")
        alert.beginSheetModal(for: window) { result in completionHandler(result == .alertFirstButtonReturn ? field.stringValue : nil) }
    }
    func makeMenu() {
        let bar = NSMenu()
        let appItem = NSMenuItem(); bar.addItem(appItem)
        let appMenu = NSMenu(); appItem.submenu = appMenu
        appMenu.addItem(withTitle: "关于日常学习", action: #selector(about), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "隐藏日常学习", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        appMenu.addItem(withTitle: "退出日常学习", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        let editItem = NSMenuItem(); bar.addItem(editItem)
        let edit = NSMenu(title: "编辑"); editItem.submenu = edit
        for (title, selector, key) in [("撤销", "undo:", "z"), ("重做", "redo:", "Z"), ("剪切", "cut:", "x"), ("复制", "copy:", "c"), ("粘贴", "paste:", "v"), ("全选", "selectAll:", "a")] {
            edit.addItem(withTitle: title, action: Selector(selector), keyEquivalent: key)
        }
        let viewItem = NSMenuItem(); bar.addItem(viewItem)
        let view = NSMenu(title: "视图"); viewItem.submenu = view
        view.addItem(withTitle: "重新载入", action: #selector(reload), keyEquivalent: "r")
        view.addItem(withTitle: "放大", action: #selector(zoomIn), keyEquivalent: "+")
        view.addItem(withTitle: "缩小", action: #selector(zoomOut), keyEquivalent: "-")
        view.addItem(withTitle: "实际大小", action: #selector(zoomReset), keyEquivalent: "0")
        view.addItem(withTitle: "显示主窗口", action: #selector(showWindow), keyEquivalent: "1")
        let windowItem = NSMenuItem(); bar.addItem(windowItem)
        let windowMenu = NSMenu(title: "窗口"); windowItem.submenu = windowMenu
        windowMenu.addItem(withTitle: "关闭窗口", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
        windowMenu.addItem(withTitle: "最小化", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        NSApp.windowsMenu = windowMenu
        let helpItem = NSMenuItem(); bar.addItem(helpItem)
        let help = NSMenu(title: "帮助"); helpItem.submenu = help
        help.addItem(withTitle: "打开数据目录", action: #selector(openData), keyEquivalent: "")
        help.addItem(withTitle: "使用说明", action: #selector(showHelp), keyEquivalent: "")
        let ownActions: Set<String> = ["about", "reload", "zoomIn", "zoomOut", "zoomReset", "showWindow", "openData", "showHelp"]
        for rootItem in bar.items {
            for item in rootItem.submenu?.items ?? [] {
                if let action = item.action, ownActions.contains(NSStringFromSelector(action)) { item.target = self }
            }
        }
        NSApp.mainMenu = bar
    }
    @objc func reload() { if readyURL != nil { web.reload() } }
    @objc func zoomIn() { web.pageZoom = min(2, web.pageZoom + 0.1) }
    @objc func zoomOut() { web.pageZoom = max(0.6, web.pageZoom - 0.1) }
    @objc func zoomReset() { web.pageZoom = 1 }
    @objc func showWindow() { window.makeKeyAndOrderFront(nil) }
    @objc func openData() { try? FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true); NSWorkspace.shared.open(dataRoot) }
    @objc func about() { NSApp.orderFrontStandardAboutPanel(options: [.applicationName: "日常学习", .applicationVersion: "1.0.0", .credits: NSAttributedString(string: "Apple Silicon 原生界面 · 本地学习数据\n关闭窗口后仍可运行定时任务；⌘Q 完全退出。")]) }
    @objc func showHelp() {
        let alert = NSAlert()
        alert.messageText = "日常学习使用说明"
        alert.informativeText = "首次使用请配置兼容 OpenAI 的模型服务并验证连接，再选择目标与材料。\n\n数据保存在：\(dataRoot.path)\n\n关闭窗口后应用继续运行，点击 Dock 图标重新打开。定时任务需要应用运行且 Mac 唤醒。⌘Q 完全退出。\n\n此版本采用本机临时签名，未经过 Apple 公证。"
        alert.runModal()
    }
}
let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
