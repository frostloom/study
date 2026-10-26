"""Start/reuse only our loopback service, then open the dashboard."""
import json,subprocess,sys,time,urllib.request,webbrowser
from pathlib import Path
root=Path(__file__).resolve().parent.parent
url='http://127.0.0.1:8765'
def running():
    try:
        with urllib.request.urlopen(url+'/api/status',timeout=2) as r:return json.load(r).get('app')=='daily-study-local'
    except Exception:return False
if not running():
    log=root/'学习台/data/server.log';log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('a') as f:
        p=subprocess.Popen([sys.executable,str(root/'学习台/server.py'),'--root',str(root)],stdout=f,stderr=f,start_new_session=True)
    for _ in range(40):
        if running():break
        if p.poll() is not None:raise SystemExit('学习台未启动，端口可能已占用。详情：'+str(log))
        time.sleep(.25)
    if not running():raise SystemExit('启动超时，请查看：'+str(log))
webbrowser.open(url)
print('日常学习台已打开：'+url+'\n关闭浏览器后服务仍运行；电脑休眠时自动安排暂停。')
