"""Portable release runtime; app resources are immutable, user data lives outside bundle."""
from pathlib import Path
import json,os,sys,threading,time
from migration import migrate_legacy,ensure_catalog
from runtime_lock import FileLock,parent_alive

def start(root,port=0,legacy_root=None,parent_pid=None,channel='stable'):
 root=Path(root).expanduser().resolve();root.mkdir(parents=True,exist_ok=True)
 run_lock=FileLock(root/'.runtime.lock')
 try:run_lock.acquire()
 except RuntimeError as error:
  print(str(error),file=sys.stderr,flush=True);raise SystemExit(1)
 if channel=='stable':migrate_legacy(root,legacy_root)
 catalog=ensure_catalog(root)
 from server import make_server,start_scheduler
 preferred=port
 if port==0:
  try:
   cached=json.loads((root/'.server-info.json').read_text(encoding='utf-8'));value=cached.get('port')
   if type(value) is int and 1024<=value<=65535:preferred=value
  except (OSError,ValueError):pass
 try:server=make_server(root,catalog,preferred,channel=channel)
 except OSError:
  if preferred==port:raise
  server=make_server(root,catalog,0,channel=channel)
 info=root/'.server-info.json';tmp=info.with_suffix('.tmp');tmp.write_text(json.dumps({'port':server.server_port,'pid':os.getpid()}),encoding='utf-8');tmp.replace(info)
 if channel=='stable':start_scheduler(server)
 print(json.dumps({'url':f'http://127.0.0.1:{server.server_port}'},ensure_ascii=False),flush=True)
 if parent_pid:
  def watch():
   while True:
    time.sleep(3)
    if not parent_alive(parent_pid):os._exit(0)
  threading.Thread(target=watch,daemon=True).start()
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close();run_lock.close()
