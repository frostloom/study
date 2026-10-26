"""Copy legacy materials and a consistent SQLite snapshot without changing originals."""
from contextlib import closing
from pathlib import Path
import json,os,shutil,sqlite3,uuid
from profile_settings import Profile

def migrate_legacy(root,legacy):
 root=Path(root).resolve();legacy=Path(legacy).expanduser().resolve() if legacy else None;root.mkdir(parents=True,exist_ok=True)
 marker=root/'学习台/data/migration.json'
 if (root/'学习台/data/catalog.json').exists() or not legacy or root==legacy or not (legacy/'学习台/data/catalog.json').is_file():return None
 stage=root/('.migration-'+uuid.uuid4().hex);stage.mkdir()
 def ignore(path,names):return [n for n in names if n in ['模型设置.json','study.sqlite3','study.sqlite3-wal','study.sqlite3-shm','临时请求','__pycache__','server.log'] or (Path(path)/n).is_symlink()]
 try:
  for rel in ['资料源','学习台/data','学习台/imports','每日计划','晚间复盘','学习记录']:
   src=legacy/rel
   if src.is_dir():shutil.copytree(src,stage/rel,ignore=ignore)
  for rel in ['学习档案.md','阅读范围与版本提醒.md']:
   if (legacy/rel).is_file():shutil.copy2(legacy/rel,stage/rel)
  data=stage/'学习台/data';data.mkdir(parents=True,exist_ok=True)
  if (legacy/'学习台/data/study.sqlite3').exists():
   with closing(sqlite3.connect(legacy/'学习台/data/study.sqlite3')) as src,closing(sqlite3.connect(data/'study.sqlite3')) as dest,dest:src.backup(dest)
  catalog=json.loads((data/'catalog.json').read_text(encoding='utf-8'))
  for a in catalog:
   path=(stage/a['path']).resolve()
   if not path.is_relative_to(stage) or not path.is_file():raise ValueError('原资料缺失或路径不安全，已保留原目录，未完成导入')
  old_cfg={}
  try:old_cfg=json.loads((legacy/'学习台/data/模型设置.json').read_text(encoding='utf-8'))
  except (OSError,ValueError):pass
  # Preserve only explicitly API-based settings; no local account credentials or CLI paths.
  if old_cfg.get('provider')=='api':
   safe={k:old_cfg[k] for k in ['provider','base_url','model','api_key'] if k in old_cfg};(data/'模型设置.json').write_text(json.dumps(safe,ensure_ascii=False),encoding='utf-8');os.chmod(data/'模型设置.json',0o600)
  profile=Profile(stage);values={'use_existing':True,'daily_minutes':180,'review_minutes':60,'goal':'继续已有学习','topics':[]}
  if (data/'study.sqlite3').exists():
   try:
    with closing(sqlite3.connect(data/'study.sqlite3')) as db,db:
     row=db.execute('SELECT body FROM plans ORDER BY day DESC LIMIT 1').fetchone()
     if row:
      p=json.loads(row[0]);values.update(daily_minutes=p.get('reading_minutes',120)+p.get('review_minutes',60),review_minutes=p.get('review_minutes',60))
      by_id={a['id']:a for a in catalog};values['topics']=list(dict.fromkeys(by_id[x['article_id']]['topic'] for x in p['items'] if x['article_id'] in by_id))
   except (sqlite3.Error,ValueError,KeyError):pass
  for k in ['auto_plan','auto_review','plan_time','review_time']:
   if k in old_cfg:values[k]=old_cfg[k]
  profile.save(values)
  info={'imported_legacy':True,'source':str(legacy),'documents':len(catalog),'originals_untouched':True};(data/'migration.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
  # Existing incomplete destination fragments are retained as recovery backups.
  recovery=root/('迁移前备份-'+uuid.uuid4().hex[:8])
  for child in list(stage.iterdir()):
   dest=root/child.name
   if dest.exists():recovery.mkdir(exist_ok=True);dest.rename(recovery/child.name)
   child.rename(dest)
  stage.rmdir();return info
 except BaseException:
  shutil.rmtree(stage,ignore_errors=True);raise

def ensure_catalog(root):
 root=Path(root);data=root/'学习台/data';data.mkdir(parents=True,exist_ok=True);path=data/'catalog.json'
 catalog=json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
 if not any(a['id']=='welcome-demo' for a in catalog):
  demo=data/'demo';demo.mkdir(exist_ok=True)
  (demo/'welcome.html').write_text('''<h2>欢迎来到日常学习</h2><h3>1. 阅读与划重点</h3><p>学习从理解一个小节开始。选中这段文字，可以划重点、写批注，或者问问AI。</p><h3>2. 带着原文提问</h3><p>AI会围绕当前小节解释，并保留当前会话的最近问答。新对话从空历史开始，旧对话仍在历史中。</p><h3>3. 用复习检验理解</h3><p>读完真实学习资料后再勾选完成。晚间复习会根据实际完成的内容出题；这篇指南不计入学习计划。</p>''',encoding='utf-8')
  catalog.append(dict(id='welcome-demo',title='认识你的学习空间',topic='使用指南',source='应用使用指南',source_url='',path='学习台/data/demo/welcome.html',format='html',minutes=5,optional=True,learning_unit=False,is_demo=True))
  tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)
 return catalog
