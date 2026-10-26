"""Run only with the learning applications closed; backup before merging."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from desktop_migration import migrate_web_settings,stage_browser_state
from runtime_lock import FileLock
p=argparse.ArgumentParser();p.add_argument('--web-root',type=Path,required=True);p.add_argument('--app-root',type=Path,required=True);p.add_argument('--backup-root',type=Path,required=True);p.add_argument('--browser-state',type=Path);args=p.parse_args()
lock=FileLock(args.app_root/'.runtime.lock').acquire()
try:
 report=migrate_web_settings(args.web_root,args.app_root,args.backup_root)
 if args.browser_state:report['browser_items']=stage_browser_state(args.app_root,json.loads(args.browser_state.read_text(encoding='utf-8')))
 print(json.dumps(report,ensure_ascii=False))
finally:lock.close()
