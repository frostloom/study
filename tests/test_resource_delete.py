import base64,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from resources import ResourceLibrary
from store import Store
from learning import Learning

class DeleteTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.rows=[];self.store=Store(self.root,self.rows);self.lib=ResourceLibrary(self.root,self.rows,self.store,None)
  self.a,self.b=self.lib.import_files([{'name':x+'.md','data':base64.b64encode(('# '+x+'\nLesson text').encode()).decode()} for x in ['One','Two']],'Go')
 def tearDown(self):self.tmp.cleanup()
 def test_delete_persists_removes_files_and_future_candidates_but_preserves_facts(self):
  self.store.replace_plan('2026-10-24',[self.a['id']],allocations={self.a['id']:1})
  self.store.toggle('2026-10-24',self.a['id'],True)
  self.store.replace_plan('2026-10-25',[self.a['id'],self.b['id']],allocations={self.a['id']:1,self.b['id']:1})
  self.lib.delete([self.a['id']])
  self.assertEqual([x['id'] for x in self.rows],[self.b['id']])
  self.assertFalse((self.root/self.a['path']).exists());self.assertFalse((self.root/self.a['original_path']).exists())
  self.assertTrue((self.root/self.b['path']).exists())
  self.assertEqual([x['article_id'] for x in self.store._load('2026-10-25')['items']],[self.b['id']])
  self.assertTrue(self.store._load('2026-10-24')['items'][0]['deleted'])
  self.assertEqual(self.store.history()[-1]['done'],1)
  self.assertEqual(self.store.handoff('2026-10-24')['completed'],[])
  restarted=Store(self.root,[self.a,self.b]);self.assertNotIn(self.a['id'],restarted.catalog)
  class Model:
   def generate(s,prompt,schema):
    candidates=json.loads(prompt.split('候选：')[-1]);assert [x['id'] for x in candidates]==[self.b['id']]
    return {'tasks':[{'article_id':self.b['id'],'minutes':self.b['minutes'],'scope':'全文'}],'note':'test'}
  plan=Learning(self.store,Model()).plan('2026-10-26');self.assertEqual(plan['items'][0]['article_id'],self.b['id'])
 def test_failed_catalog_write_rolls_back_deletion(self):
  with patch('resources.os.replace',side_effect=OSError('disk full')):
   with self.assertRaises(OSError):self.lib.delete([self.a['id']])
  self.assertIn(self.a['id'],self.store.catalog)
  self.assertTrue((self.root/self.a['path']).exists())
  self.assertIn(self.a['id'],Store(self.root,self.rows).catalog)
 def test_invalid_selection_rejected_before_any_deletion(self):
  for ids in [[],['missing'],[self.a['id'],'missing'],'bad']:
   with self.assertRaises(ValueError):self.lib.delete(ids)
  self.assertEqual(len(self.rows),2)
 def test_module_children_deleted_shared_and_external_paths_preserved(self):
  child={**self.a,'id':'child','parent_unit':self.a['id'],'learning_unit':False}
  shared={**self.b,'id':'shared','path':self.a['path']}
  self.rows.extend([child,shared]);self.store.catalog.update({x['id']:x for x in [child,shared]})
  self.lib.delete([self.a['id']]);self.assertNotIn('child',self.store.catalog)
  self.assertTrue((self.root/self.a['path']).exists())
 def test_deleted_review_still_can_be_graded_from_question_context(self):
  self.store.save_review('2026-10-24',{'questions':[{'id':'q','article_ids':[self.a['id']],'question':'Explain','criteria':'Basics','reference_answer':'Reference','answer':'','grade':None}]})
  self.lib.delete([self.a['id']])
  class Model:
   def generate(s,prompt,schema):return {'score':2,'feedback':'ok','follow_up':'why','reference_answer':'Reference'}
  review=Learning(self.store,Model()).answer_review('2026-10-24','q','My answer')
  self.assertEqual(review['questions'][0]['grade']['score'],2)

 def test_completed_deleted_task_survives_other_task_check_and_plan_edit(self):
  day='2026-10-24';aid=self.a['id'];bid=self.b['id']
  self.store.replace_plan(day,[aid,bid],allocations={aid:1,bid:1},scopes={aid:'Original section'})
  self.store.toggle(day,aid,True);self.lib.delete([aid])
  self.store.toggle(day,bid,True)
  self.store.add_article(day,bid)
  p=self.store._load(day)
  self.assertEqual(p['completed_minutes'],2)
  archived=next(x for x in p['items'] if x['article_id']==aid)
  self.assertEqual(archived['scope'],'Original section');self.assertTrue(archived['done'])

 def test_whole_source_removes_unindexed_attachments_but_preserves_active_source(self):
  folder=self.root/'资料源/Book';folder.mkdir(parents=True);(folder/'LICENSE').write_text('license');(folder/'diagram.svg').write_text('<svg/>')
  a={**self.a,'id':'source-a','source':'Book','path':'资料源/Book/a.md'}
  b={**self.b,'id':'source-b','source':'Book','path':'资料源/Book/b.md'}
  (folder/'a.md').write_text('a');(folder/'b.md').write_text('b')
  self.rows.extend([a,b]);self.store.catalog.update({x['id']:x for x in [a,b]})
  self.lib.delete([a['id']]);self.assertTrue((folder/'diagram.svg').exists())
  self.lib.delete([b['id']]);self.assertFalse(folder.exists())
 def test_import_metadata_removed_when_last_document_deleted(self):
  folder=(self.root/self.a['path']).parent;(folder/'source-manifest.json').write_text('{}')
  self.lib.delete([self.a['id']]);self.assertFalse(folder.exists())
