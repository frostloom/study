# 安装、数据与开发预览

Mac：打开适合本机处理器的DMG，把日常学习拖到Applications，或解压ZIP。当前无DeveloperID/Apple公证身份。Windows10/11 x64：运行setup安装包，或解压便携ZIP；使用系统WebView2运行时。若缺失，应用会引导至微软官方下载。发行者签名证书尚未配置。请勿全局关闭系统防护。

模型采用OpenAI兼容ChatCompletions接口。首次设置可自由填写目标、检索预览并选择资料、设置每日时间和可选早晚安排。修改设置不丢失学习记录。

正式数据目录：Mac为~/Library/Application Support/日常学习；Windows为%LOCALAPPDATA%/DailyStudy。应用本体可以替换升级；请勿删除数据目录。模型密钥保存在本机配置，不随GitHub软件包发布。备份应妥善保管。

应用启动后自动在后台检查GitHub最新正式Release，持续运行每6小时再检查。发现适用平台的新版本，左下角自动显示“有新版本，立即更新”，点击查看说明并下载。关闭应用安装新版即可继续使用原数据。1.0.0需先手动升级一次，之后才具备更新提示。

开发者：创建Python3.12虚拟环境并安装requirements-build.txt，运行python tools/preview.py。预览版使用独立数据目录，原生应用有独立名称/身份；不自动导入正式数据和定时学习任务。也可设置BUILD_CHANNEL=preview构建原生预览版。模型配置与资料需自行在预览环境添加，避免实验污染日常记录。

关闭Mac窗口后仍可运行定时任务，CmdQ完全退出。Windows关闭窗口即退出并结束所属后端。所有自动安排都需要电脑唤醒与应用运行，不注册系统后台服务。
