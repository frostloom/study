import unittest,tempfile
from pathlib import Path
try:from profile_settings import Profile
except ImportError:Profile=None
class ProfileTests(unittest.TestCase):
 def test_wizard_draft_persists_and_back_navigation_does_not_complete(self):
  self.assertIsNotNone(Profile)
  with tempfile.TemporaryDirectory() as t:
   p=Profile(Path(t));p.save({'goal':'学习Go','topics':['Go后端'],'wizard_step':2,'daily_minutes':45,'review_minutes':15})
   q=Profile(Path(t));self.assertEqual(q.get()['goal'],'学习Go');self.assertFalse(q.get()['onboarding_completed']);self.assertEqual(q.budget(),(30,15))
 def test_invalid_budget_cannot_overwrite_saved_settings(self):
  self.assertIsNotNone(Profile)
  with tempfile.TemporaryDirectory() as t:
   p=Profile(Path(t));before=p.get()
   for patch in [{'daily_minutes':10},{'review_minutes':999},{'daily_minutes':True},{'plan_time':'25:00'}]:
    with self.assertRaises(ValueError):p.save(patch)
   self.assertEqual(p.get(),before)
 def test_draft_cannot_skip_onboarding(self):
  self.assertIsNotNone(Profile)
  with tempfile.TemporaryDirectory() as t:
   p=Profile(Path(t));p.save({'onboarding_completed':True});self.assertFalse(p.get()['onboarding_completed'])
