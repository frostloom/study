"""Open the native development preview against this editable source checkout."""
from pathlib import Path
import os,subprocess,sys
root=Path(__file__).resolve().parents[1]
if __name__=='__main__':
 if sys.platform=='darwin':
  app=root.parent/'日常学习预览版.app'
  if not app.exists():app=root/'release-preview/日常学习预览版.app'
  if not app.exists():raise SystemExit('请先使用 BUILD_CHANNEL=preview BUILD_DIST="$PWD/release-preview" tools/build_macos.sh 构建原生预览窗口。')
  subprocess.run(['open','-a',str(app),'--args','--source-dir',str(root),'--python',sys.executable],check=True)
 elif sys.platform=='win32':
  app=root/'release-build/windows-stage/DailyStudy.exe';marker=app.parent/'channel.txt'
  if not marker.exists() or marker.read_text(encoding='utf-8').strip()!='preview':raise SystemExit('请先运行 tools/build_windows.ps1 -Channel preview 构建预览窗口。')
  subprocess.Popen([str(app),'--source-dir',str(root),'--python',sys.executable],creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
 else:raise SystemExit('Native preview supports macOS and Windows')
