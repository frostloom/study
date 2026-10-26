import json,tempfile,unittest,hashlib
from pathlib import Path
from migration import migrate_legacy,ensure_catalog
from store import Store
from model import ModelClient
from profile_settings import Profile
class MigrationTests(unittest.TestCase):
 def test_legacy_materials_progress_and_chat_copied_without_changing_original(self):
  with tempfile.TemporaryDirectory() as t:
   base=Path(t);old=base/'old';dest=base/'new';(old/'资料源').mkdir(parents=True);source=old/'资料源/a.md';source.write_text('# 原资料\n用户原文',encoding='utf-8')
   c=[dict(id='a',title='原资料',topic='Go',path='资料源/a.md',format='markdown',source='本人资料',source_url='',minutes=30,learning_unit=True)]
   s=Store(old,c);(s.data/'catalog.json').write_text(json.dumps(c),encoding='utf-8');s.replace_plan('2026-10-26',['a']);s.toggle('2026-10-26','a',True);s.add_chat('a','原问题','原答案')
   (s.data/'模型设置.json').write_text(json.dumps({'provider':'codex','cli_path':'DO_NOT_COPY'}),encoding='utf-8');before=source.read_bytes()
   result=migrate_legacy(dest,old);self.assertTrue(result['imported_legacy']);self.assertEqual((dest/'资料源/a.md').read_bytes(),before);self.assertEqual(source.read_bytes(),before)
   new=Store(dest,ensure_catalog(dest));self.assertIn('a',new.read_ids());self.assertEqual(new.chats(article_id='a')[0]['reply'],'原答案');self.assertEqual(ModelClient(dest).settings()['model'],'');self.assertFalse(Profile(dest).get()['onboarding_completed'])
   self.assertIsNone(migrate_legacy(dest,old))
 def test_bad_legacy_catalog_does_not_publish_partial_migration(self):
  with tempfile.TemporaryDirectory() as t:
   old=Path(t)/'old';new=Path(t)/'new';(old/'学习台/data').mkdir(parents=True);(old/'学习台/data/catalog.json').write_text(json.dumps([dict(id='bad',path='missing.md')]),encoding='utf-8')
   with self.assertRaises(ValueError):migrate_legacy(new,old)
   self.assertFalse((new/'学习台/data/catalog.json').exists());self.assertTrue((old/'学习台/data/catalog.json').exists())
