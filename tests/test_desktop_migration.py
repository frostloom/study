from contextlib import closing
import unittest,tempfile,json,sqlite3
from pathlib import Path
from store import Store
from desktop_migration import migrate_web_settings,validate_browser_state
class DesktopMigrationTests(unittest.TestCase):
 def test_merge_preserves_desktop_plan_and_adds_missing_history_and_settings(self):
  with tempfile.TemporaryDirectory() as t:
   web=Path(t)/'web';app=Path(t)/'app';backup=Path(t)/'backup'
   for root in [web,app]:
    d=root/'学习台/data';d.mkdir(parents=True);(d/'catalog.json').write_text('[]',encoding='utf-8');Store(root,[])
   cfg={'provider':'api','base_url':'https://example.com/v1','model':'fixture','api_key':'test-only','auto_plan':True,'auto_review':False,'plan_time':'09:00','review_time':'22:00'}
   (web/'学习台/data/模型设置.json').write_text(json.dumps(cfg),encoding='utf-8')
   with closing(sqlite3.connect(web/'学习台/data/study.sqlite3')) as db,db:
    db.execute('INSERT INTO prior_readings VALUES (?,?,?)',('prior','2026-10-25','read'))
    db.execute('INSERT INTO plans VALUES (?,?)',('2026-10-26','{"source":"web"}'))
   with closing(sqlite3.connect(app/'学习台/data/study.sqlite3')) as db,db:db.execute('INSERT INTO plans VALUES (?,?)',('2026-10-26','{"source":"desktop"}'))
   result=migrate_web_settings(web,app,backup)
   with closing(sqlite3.connect(app/'学习台/data/study.sqlite3')) as db,db:
    self.assertEqual(json.loads(db.execute('SELECT body FROM plans').fetchone()[0])['source'],'desktop')
    self.assertEqual(db.execute('SELECT count(*) FROM prior_readings').fetchone()[0],1)
   self.assertEqual(json.loads((app/'学习台/data/模型设置.json').read_text(encoding='utf-8'))['api_key'],'test-only')
   p=json.loads((app/'学习台/data/profile.json').read_text(encoding='utf-8'));self.assertTrue(p['auto_plan']);self.assertEqual(p['plan_time'],'09:00')
   self.assertEqual(len(result['conflicts']),1);self.assertTrue((backup/'web/study.sqlite3').is_file());self.assertTrue((backup/'app/study.sqlite3').is_file())
 def test_browser_transfer_only_study_preferences_no_arbitrary_secrets(self):
  value=validate_browser_state({'study-theme':'paper','study-draft:2026-10-26:q1':'my draft','unrelated-token':'secret'})
  self.assertEqual(value,{'study-theme':'paper','study-draft:2026-10-26:q1':'my draft'})
  with self.assertRaises(ValueError):validate_browser_state({'study-ai-draft:article':'x'*200001})
 def test_existing_desktop_preferences_preserved_and_newer_web_check_reported(self):
  from profile_settings import Profile
  with tempfile.TemporaryDirectory() as t:
   web=Path(t)/'web';app=Path(t)/'app'
   for root in [web,app]:
    Store(root,[]);(root/'学习台/data/catalog.json').write_text('[]',encoding='utf-8')
   Profile(app).save({'goal':'desktop goal','auto_plan':False,'plan_time':'11:00'})
   Profile(web).save({'goal':'web goal','auto_plan':True,'plan_time':'09:00'})
   for root,done,when in [(web,1,'2026-10-26'),(app,0,'2026-10-25')]:
    with closing(sqlite3.connect(root/'学习台/data/study.sqlite3')) as db,db:db.execute('INSERT INTO checks VALUES (?,?,?,?)',('2026-10-26','a',done,when))
   r=migrate_web_settings(web,app,Path(t)/'backup');p=Profile(app).get()
   self.assertEqual(p['goal'],'desktop goal');self.assertFalse(p['auto_plan']);self.assertEqual(p['plan_time'],'11:00')
   self.assertTrue(any(x['table']=='checks' for x in r['conflicts']))
   self.assertTrue(any(x['table']=='profile' and x['field']=='goal' for x in r['conflicts']))
 def test_fresh_desktop_imports_web_goal_budget_and_choices(self):
  from profile_settings import Profile
  with tempfile.TemporaryDirectory() as t:
   web=Path(t)/'web';app=Path(t)/'app'
   Store(web,[]);(web/'学习台/data/catalog.json').write_text('[]',encoding='utf-8')
   Profile(web).save({'goal':'learn photography','daily_minutes':120,'review_minutes':30,'resource_ids':['chosen']})
   migrate_web_settings(web,app,Path(t)/'backup');p=Profile(app).get()
   self.assertEqual(p['goal'],'learn photography');self.assertEqual(p['daily_minutes'],120);self.assertEqual(p['resource_ids'],['chosen'])
 def test_same_id_changed_material_retains_both_and_reports_catalog_conflict(self):
  with tempfile.TemporaryDirectory() as t:
   web=Path(t)/'web';app=Path(t)/'app'
   for root,title,text in [(web,'new title','web material'),(app,'old title','desktop material')]:
    row=dict(id='same',title=title,path='资料源/a.md',topic='topic');Store(root,[row]);(root/'资料源').mkdir();(root/'资料源/a.md').write_text(text,encoding='utf-8');(root/'学习台/data/catalog.json').write_text(json.dumps([row]),encoding='utf-8')
   backup=Path(t)/'backup';r=migrate_web_settings(web,app,backup)
   self.assertEqual((app/'资料源/a.md').read_text(encoding='utf-8'),'desktop material')
   material=next(x for x in r['conflicts'] if x['table']=='material')
   self.assertEqual((backup/material['web_copy']).read_text(encoding='utf-8'),'web material')
   self.assertTrue(any(x['table']=='catalog' for x in r['conflicts']))
