import tempfile,unittest
from pathlib import Path
from store import Store
class ReportedReadingTests(unittest.TestCase):
 def test_self_reported_reading_is_seen_without_inventing_daily_completion(self):
  with tempfile.TemporaryDirectory() as t:
   s=Store(Path(t),[dict(id='go1',title='基础',topic='Go后端',minutes=90)])
   with s.connect() as c:c.execute('INSERT INTO prior_readings VALUES (?,?,?)',('go1','2026-10-25','用户自报已读，实际阅读日期未知'))
   self.assertIn('go1',s.read_ids());self.assertEqual(s.history(),[])
   self.assertEqual(s.handoff('2026-10-25')['completed'],[])
