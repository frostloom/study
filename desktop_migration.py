"""Explicit local migration; never runs in preview or uploads personal state."""
from contextlib import closing
from pathlib import Path
import json,os,shutil,sqlite3,uuid,hashlib
from profile_settings import Profile,DEFAULTS

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
   with closing(sqlite3.connect(f'file:{data/"study.sqlite3"}?mode=ro',uri=True)) as src,closing(sqlite3.connect(folder/'study.sqlite3')) as dst,dst:src.backup(dst)
   os.chmod(folder/'study.sqlite3',0o600)
 report=dict(backup=str(backup),added_records=0,added_materials=0,conflicts=[])
 original=json.loads((wd/'catalog.json').read_text(encoding='utf-8'));current=json.loads((ad/'catalog.json').read_text(encoding='utf-8')) if (ad/'catalog.json').exists() else []
 ids={x['id'] for x in current}
 by_id={x['id']:x for x in current}
 for row in original:
  source=(web/row['path']).resolve();dest=(app/row['path']).resolve()
  if not source.is_relative_to(web) or not dest.is_relative_to(app) or not source.is_file():raise ValueError('原资料缺失或路径不安全')
  if row['id'] in ids:
   old=by_id[row['id']];existing=(app/old['path']).resolve()
   if not existing.is_relative_to(app):raise ValueError('目标资料路径不安全')
   if old!=row:report['conflicts'].append(dict(table='catalog',id=row['id'],kept='desktop',web_copy='web/catalog.json'))
   if not existing.exists():existing.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,existing)
   elif existing.read_bytes()!=source.read_bytes():
    saved=backup/'web/materials'/(hashlib.sha256(str(row['id']).encode()).hexdigest()[:24]+source.suffix)
    saved.parent.mkdir(exist_ok=True);shutil.copy2(source,saved);os.chmod(saved,0o600)
    report['conflicts'].append(dict(table='material',id=row['id'],kept='desktop',web_copy=str(saved.relative_to(backup))))
   continue
  if row['id'] not in ids:
   dest.parent.mkdir(parents=True,exist_ok=True)
   if dest.exists() and source.read_bytes()!=dest.read_bytes():raise ValueError('目标存在不同内容的同名资料，已保留备份，请先处理冲突')
   if not dest.exists():shutil.copy2(source,dest)
   current.append(row);ids.add(row['id']);report['added_materials']+=1
 (ad/'catalog.json').write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf-8')
 if (wd/'study.sqlite3').exists():
  from store import Store
  Store(app,current)
  with closing(sqlite3.connect(backup/'web/study.sqlite3')) as src,closing(sqlite3.connect(ad/'study.sqlite3')) as dst,dst:
   src.row_factory=sqlite3.Row
   for table in ['plans','checks','annotations','chat_sessions','reviews','prior_readings','visits','conversations']:
    schema=list(src.execute('PRAGMA table_info('+table+')'));columns=[r[1] for r in schema];keys=[r[1] for r in schema if r[5]]
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
     elif keys:
      old=dst.execute('SELECT '+','.join(cols)+' FROM '+table+' WHERE '+' AND '.join(k+' IS ?' for k in keys),[vals[k] for k in keys]).fetchone()
      if old and tuple(old)!=tuple(vals[x] for x in cols):report['conflicts'].append(dict(table=table,key={k:vals[k] for k in keys},kept='desktop',web_copy='backup/web/study.sqlite3'))
 cfg={}
 if (wd/'模型设置.json').is_file():cfg=json.loads((wd/'模型设置.json').read_text(encoding='utf-8'))
 if cfg.get('provider')=='api' and not (ad/'模型设置.json').exists():
  safe={k:cfg[k] for k in ['provider','base_url','model','api_key'] if k in cfg};(ad/'模型设置.json').write_text(json.dumps(safe,ensure_ascii=False),encoding='utf-8');os.chmod(ad/'模型设置.json',0o600)
 profile=Profile(app);existing=profile.path.exists();prefs={k:cfg[k] for k in ['auto_plan','auto_review','plan_time','review_time'] if k in cfg}
 if (wd/'profile.json').exists():prefs.update(json.loads((wd/'profile.json').read_text(encoding='utf-8')))
 prefs={k:v for k,v in prefs.items() if k in DEFAULTS and k not in ['version','onboarding_completed']}
 if existing:
  now=profile.get()
  for k,v in prefs.items():
   if now.get(k)!=v:report['conflicts'].append(dict(table='profile',field=k,kept='desktop',web_copy='backup/web'))
 else:profile.save(prefs)
 if cfg.get('provider')=='api' and (ad/'模型设置.json').exists():
  desktop=json.loads((ad/'模型设置.json').read_text(encoding='utf-8'))
  if any(desktop.get(k)!=cfg.get(k) for k in ['base_url','model','api_key']):report['conflicts'].append(dict(table='model',kept='desktop',web_copy='backup/web/模型设置.json'))
 for name in ['学习档案.md','阅读范围与版本提醒.md']:
  if (web/name).is_file() and not (app/name).exists():shutil.copy2(web/name,app/name)
 (backup/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');return report
