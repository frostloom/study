import tempfile,unittest,json
from pathlib import Path
from store import Store
from learning import Learning
from profile_settings import Profile

class DayEditTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.day='2026-10-26'
  self.rows=[dict(id=x,title=x,topic='Go',source='Book',path=x+'.md',source_url='',minutes=90,learning_unit=True) for x in ['a','b','c']]
  for a in self.rows:(self.root/a['path']).write_text('# '+a['title']+'\n## Basics\nFull text')
  Profile(self.root).save({'use_existing':True,'daily_minutes':180,'review_minutes':60})
  self.store=Store(self.root,self.rows)
 def tearDown(self):self.tmp.cleanup()
 def test_manual_start_add_and_adjust_day_does_not_change_default_budget(self):
  p=self.store.edit_day(self.day,{'action':'add','article_id':'a','minutes':30,'scope':'Basics'})
  self.assertEqual(p['items'][0]['scope'],'Basics')
  self.store.edit_day(self.day,{'action':'add','article_id':'b','minutes':90})
  p=self.store.edit_day(self.day,{'action':'add','article_id':'c','minutes':60})
  self.assertEqual(p['reading_minutes'],180);self.assertEqual(self.store.budget(),(120,60))
  p=self.store.edit_day(self.day,{'action':'update','article_id':'a','minutes':15,'scope':'First half'})
  self.assertEqual(p['items'][0]['minutes'],15)
 def test_remove_completed_retains_facts_but_drops_review_scope_and_pending(self):
  self.store.edit_day(self.day,{'action':'add','article_id':'a','minutes':30});self.store.toggle(self.day,'a',True)
  self.store.save_review(self.day,{'questions':[{'id':'q1','article_ids':['a'],'answer':'Saved','grade':{'score':2}},{'id':'q2','article_ids':['a'],'answer':'','grade':None}],'completed_article_ids':['a'],'status':'进行中'})
  p=self.store.edit_day(self.day,{'action':'remove','article_id':'a'})
  self.assertEqual(p['items'],[]);self.assertEqual(self.store.handoff(self.day)['completed'],[])
  self.assertEqual(self.store.history()[0]['done'],1);self.assertEqual(self.store.history()[0]['completed_minutes'],30)
  self.assertEqual([q['id'] for q in self.store.review(self.day)['questions']],['q1'])
  self.assertEqual(self.store.review(self.day)['questions'][0]['answer'],'Saved')
 def test_removed_pending_not_reintroduced_as_tomorrow_task(self):
  self.store.edit_day(self.day,{'action':'add','article_id':'a','minutes':30});self.store.edit_day(self.day,{'action':'remove','article_id':'a'})
  class Model:
   def generate(s,prompt,schema):
    candidates=json.loads(prompt.split('候选：')[-1]);assert 'a' not in {x['id'] for x in candidates}
    return {'tasks':[{'article_id':'b','minutes':90,'scope':'全文'}],'note':'test'}
  self.assertEqual(Learning(self.store,Model()).plan('2026-10-27')['items'][0]['article_id'],'b')
 def test_invalid_edits_leave_plan_unchanged(self):
  self.store.edit_day(self.day,{'action':'add','article_id':'a','minutes':30});before=self.store._load(self.day)
  for patch in [{'action':'add','article_id':'missing'},{'action':'update','article_id':'a','minutes':-1},{'action':'budget','reading_minutes':2,'review_minutes':10},{'action':'budget','reading_minutes':480,'review_minutes':60}]:
   with self.assertRaises(ValueError):self.store.edit_day(self.day,patch)
   self.assertEqual(before,self.store._load(self.day))
 def test_checked_scope_change_requires_unchecking_and_new_checks_refresh_review(self):
  self.store.edit_day(self.day,{'action':'add','article_id':'a','minutes':30});self.store.toggle(self.day,'a',True)
  with self.assertRaises(ValueError):self.store.edit_day(self.day,{'action':'update','article_id':'a','minutes':20})
  self.store.save_review(self.day,{'questions':[{'id':'q','article_ids':['a'],'answer':'','grade':None}],'completed_article_ids':['a'],'status':'待作答'})
  self.store.toggle(self.day,'a',False)
  self.assertEqual(self.store.review(self.day)['questions'],[])
 def test_atomic_save_rejects_invalid_batch_and_stale_revision(self):
  p=self.store.edit_day(self.day,{'action':'add','article_id':'a','minutes':30});before=self.store._load(self.day)
  with self.assertRaises(ValueError):self.store.edit_day(self.day,{'action':'save','tasks':[{'article_id':'b','minutes':20},{'article_id':'missing','minutes':20}]})
  self.assertEqual(before,self.store._load(self.day))
  p=self.store.edit_day(self.day,{'action':'save','expected_revision':p['revision'],'tasks':[{'article_id':'b','minutes':20,'scope':'First section'}],'reading_minutes':30,'review_minutes':10})
  self.assertEqual(p['items'][0]['article_id'],'b');self.assertEqual(p['review_minutes'],10)
  with self.assertRaises(ValueError):self.store.edit_day(self.day,{'action':'save','expected_revision':before['revision'],'tasks':[]})
  self.assertEqual(self.store._load(self.day),p)
 def test_edit_scope_after_uncheck_allows_review_supplement_keeps_old_answer(self):
  self.store.edit_day(self.day,{'action':'add','article_id':'a','minutes':30,'scope':'First section'});self.store.toggle(self.day,'a',True)
  self.store.save_review(self.day,{'questions':[{'id':'old','article_ids':['a'],'answer':'Real answer','grade':{'score':2}}],'completed_article_ids':['a'],'status':'已完成'})
  self.store.toggle(self.day,'a',False);self.store.edit_day(self.day,{'action':'update','article_id':'a','minutes':20,'scope':'Second section'});self.store.toggle(self.day,'a',True)
  class Model:
   def generate(s,prompt,schema):
    assert 'Second section' in prompt
    return {'questions':[{'question':'Explain second section','article_ids':['a'],'reference_answer':'ref','criteria':'criteria'}]}
  r=Learning(self.store,Model()).start_review(self.day)
  self.assertEqual(len(r['questions']),2);self.assertEqual(r['questions'][0]['answer'],'Real answer')
 def test_removed_completed_partial_cannot_be_readded_as_completed_new_scope(self):
  self.store.edit_day(self.day,{'action':'add','article_id':'a','minutes':20,'scope':'First'});self.store.toggle(self.day,'a',True)
  self.store.edit_day(self.day,{'action':'remove','article_id':'a'})
  with self.assertRaises(ValueError):self.store.edit_day(self.day,{'action':'save','tasks':[{'article_id':'a','minutes':90,'scope':'Whole'}]})
  self.assertEqual(self.store.history()[0]['completed_minutes'],20);self.assertNotIn('a',self.store.read_ids())
  p=self.store.edit_day(self.day,{'action':'add','article_id':'a','minutes':20,'scope':'First'})
  self.assertEqual(p['items'][0]['minutes'],20);self.assertTrue(p['items'][0]['done'])
 def test_unchecking_joint_question_invalidates_remaining_coverage(self):
  for aid in ['a','b']:
   self.store.edit_day(self.day,{'action':'add','article_id':aid,'minutes':30});self.store.toggle(self.day,aid,True)
  self.store.save_review(self.day,{'questions':[{'id':'joint','article_ids':['a','b'],'answer':'','grade':None}],'completed_article_ids':['a','b']})
  self.store.toggle(self.day,'a',False)
  self.assertEqual(self.store.review(self.day)['completed_article_ids'],[])
 def test_visit_days_do_not_expire_explicit_removal(self):
  self.store.edit_day(self.day,{'action':'add','article_id':'a','minutes':30});self.store.edit_day(self.day,{'action':'remove','article_id':'a'})
  with self.store.connect() as c:
   for day in ['2026-10-27','2026-10-28','2026-10-29']:c.execute('INSERT INTO visits VALUES (?,?,?,?)',(day,'b',1,'now'))
  class Model:
   def generate(s,prompt,schema):
    assert 'a' not in {x['id'] for x in json.loads(prompt.split('候选：')[-1])}
    return {'tasks':[{'article_id':'b','minutes':90,'scope':'Full'}],'note':'test'}
  Learning(self.store,Model()).plan('2026-10-30')
