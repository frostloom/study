"""Open the native development preview against this editable source checkout."""
from pathlib import Path
import os,subprocess,sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from app_info import default_data_root

def prepare_preview(source,python,data=None):
 source=Path(source).resolve();python=Path(python).absolute();data=Path(data or default_data_root('preview'))
 if not (source/'backend_entry.py').is_file() or not python.is_file():raise ValueError('找不到开发源码或Python，请检查开发环境')
 if any('\n' in str(p) or '\r' in str(p) for p in [source,python]):raise ValueError('开发路径不能包含换行')
 data.mkdir(parents=True,exist_ok=True);path=data/'.development-source';tmp=path.with_suffix('.tmp');tmp.write_text(str(source)+'\n'+str(python)+'\n',encoding='utf-8');tmp.chmod(0o600);tmp.replace(path)

if __name__=='__main__':
 prepare_preview(root,sys.executable)
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
