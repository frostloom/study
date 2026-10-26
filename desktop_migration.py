"""Explicit local migration; never runs in preview or uploads personal state."""
from pathlib import Path
import json,os,shutil,sqlite3,uuid
from profile_settings import Profile

def validate_browser_state(items):
 if not isinstance(items,dict) or len(items)>3000:raise ValueError('浏览器资料格式无效')
 allowed={}
 for k,v in items.items():
  if not isinstance(k,str) or not (k=='study-theme' or k.startswith(('study-draft:','study-ai-draft:','study-active-session:'))):continue
  if not isinstance(v,str) or len(k)>500 or len(v)>200000:raise ValueError('浏览器草稿过大')
  if k=='study-theme' and v not in ['white','dark','paper']:continue
  allowed[k]=v
 if len(json.dumps(allowed,ensure_ascii=False).encode())>2*1024*1024:raise ValueError('浏览器草稿超过2MB')
 return allowed

def stage_browser_state(root,items):
 value=dict(id=uuid.uuid4().hex,items=validate_browser_state(items));p=Path(root)/'学习台/data/browser-transfer.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8');os.chmod(p,0o600);return len(value['items'])

def migrate_web_settings(web_root,app_root,backup_root):
 web,app,backup=map(lambda p:Path(p).resolve(),[web_root,app_root,backup_root])
 if web==app or web.is_relative_to(app) or app.is_relative_to(web):raise ValueError('原数据与目标数据必须互相独立')
 wd=web/'学习台/data';ad=app/'学习台/data';ad.mkdir(parents=True,exist_ok=True)
 backup.mkdir(parents=True,exist_ok=False);os.chmod(backup,0o700)
 for name,data in [('web',wd),('app',ad)]:
  folder=backup/name;folder.mkdir()
  for n in ['模型设置.json','profile.json','catalog.json','browser-transfer.json']:
   if (data/n).is_file():shutil.copy2(data/n,folder/n);os.chmod(folder/n,0o600)
  if (data/'study.sqlite3').exists():
   with sqlite3.connect(f'file:{data/"study.sqlite3"}?mode=ro',uri=True) as src,sqlite3.connect(folder/'study.sqlite3') as dst:src.backup(dst)
   os.chmod(folder/'study.sqlite3',0o600)
 report=dict(backup=str(backup),added_records=0,added_materials=0,conflicts=[])
 original=json.loads((wd/'catalog.json').read_text(encoding='utf-8'));current=json.loads((ad/'catalog.json').read_text(encoding='utf-8')) if (ad/'catalog.json').exists() else []
 ids={x['id'] for x in current}
 for row in original:
  source=(web/row['path']).resolve();dest=(app/row['path']).resolve()
  if not source.is_relative_to(web) or not dest.is_relative_to(app) or not source.is_file():raise ValueError('原资料缺失或路径不安全')
  if row['id'] not in ids:
   dest.parent.mkdir(parents=True,exist_ok=True)
   if dest.exists() and source.read_bytes()!=dest.read_bytes():raise ValueError('目标存在不同内容的同名资料，已保留备份，请先处理冲突')
   if not dest.exists():shutil.copy2(source,dest)
   current.append(row);ids.add(row['id']);report['added_materials']+=1
 (ad/'catalog.json').write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf-8')
 if (wd/'study.sqlite3').exists():
  from store import Store
  Store(app,current)
  with sqlite3.connect(backup/'web/study.sqlite3') as src,sqlite3.connect(ad/'study.sqlite3') as dst:
   src.row_factory=sqlite3.Row
   for table in ['plans','checks','annotations','chat_sessions','reviews','prior_readings','visits','conversations']:
    columns=[r[1] for r in src.execute('PRAGMA table_info('+table+')')]
    if not columns:continue
    for row in src.execute('SELECT * FROM '+table):
     vals=dict(row)
     if table=='conversations':
      cols=[x for x in columns if x!='id'];where=' AND '.join(f'{x} IS ?' for x in cols)
      if dst.execute('SELECT 1 FROM conversations WHERE '+where,[vals[x] for x in cols]).fetchone():continue
     else:cols=columns
     before=dst.total_changes
     dst.execute('INSERT OR IGNORE INTO '+table+' ('+','.join(cols)+') VALUES ('+','.join('?' for _ in cols)+')',[vals[x] for x in cols])
     if dst.total_changes>before:report['added_records']+=1
     elif table in ['plans','reviews']:
      old=dst.execute('SELECT body FROM '+table+' WHERE day=?',(vals['day'],)).fetchone()
      if old and old[0]!=vals['body']:report['conflicts'].append(dict(table=table,day=vals['day'],kept='desktop',web_copy='backup/web/study.sqlite3'))
 cfg={}
 if (wd/'模型设置.json').is_file():cfg=json.loads((wd/'模型设置.json').read_text(encoding='utf-8'))
 if cfg.get('provider')=='api' and not (ad/'模型设置.json').exists():
  safe={k:cfg[k] for k in ['provider','base_url','model','api_key'] if k in cfg};(ad/'模型设置.json').write_text(json.dumps(safe,ensure_ascii=False),encoding='utf-8');os.chmod(ad/'模型设置.json',0o600)
 profile=Profile(app);profile.save({k:cfg[k] for k in ['auto_plan','auto_review','plan_time','review_time'] if k in cfg})
 for name in ['学习档案.md','阅读范围与版本提醒.md']:
  if (web/name).is_file() and not (app/name).exists():shutil.copy2(web/name,app/name)
 (backup/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');return report
