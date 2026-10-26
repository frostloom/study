import tempfile,unittest
from pathlib import Path
from store import Store
from profile_settings import Profile
class BudgetTests(unittest.TestCase):
 def test_custom_budget_and_partial_reading_not_full_completion(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);Profile(root).save({'daily_minutes':30,'review_minutes':10})
   s=Store(root,[dict(id='a',title='长模块',topic='Go',minutes=90,source_url='',path='a.md')])
   p=s.replace_plan('2026-10-26',['a'],allocations={'a':20},scopes={'a':'先读第一小节'})
   self.assertEqual(p['reading_minutes'],20);self.assertEqual(p['review_minutes'],10);self.assertTrue(p['items'][0]['partial'])
   s.toggle('2026-10-26','a',True);self.assertNotIn('a',s.read_ids());self.assertTrue(s.handoff('2026-10-26')['completed'][0]['partial'])
 def test_existing_plan_budget_is_retained_after_settings_change(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);p=Profile(root);p.save({'daily_minutes':180,'review_minutes':60});s=Store(root,[dict(id='a',title='模块',topic='Go',minutes=90,source_url='',path='a.md')]);s.replace_plan('2026-10-26',['a']);p.save({'daily_minutes':30,'review_minutes':10})
   self.assertEqual(s._load('2026-10-26')['reading_minutes'],120)
 def test_manual_add_preserves_checked_partial_scope(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);Profile(root).save({'daily_minutes':180,'review_minutes':60})
   rows=[dict(id='a',title='长模块',topic='Go',minutes=90,source_url='',path='a.md'),dict(id='b',title='短模块',topic='Go',minutes=20,source_url='',path='b.md')];s=Store(root,rows)
   s.replace_plan('2026-10-26',['a'],allocations={'a':20},scopes={'a':'只读第一小节'});s.toggle('2026-10-26','a',True)
   p=s.add_article('2026-10-26','b');a=p['items'][0]
   self.assertEqual(a['minutes'],20);self.assertTrue(a['partial']);self.assertEqual(a['scope'],'只读第一小节');self.assertNotIn('a',s.read_ids())
