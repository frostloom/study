import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
try:from navigation import chapter_units, visible_documents
except ImportError:chapter_units=visible_documents=None

class NavigationTests(unittest.TestCase):
 def test_original_chapter_keeps_all_questions_in_source_order(self):
  self.assertIsNotNone(chapter_units)
  b='<h1>Go</h1><h2 id="basics">1. 基础</h2><h3 id="q1">1.1协程</h3><p>A</p><h3 id="q2">1.2线程</h3><p>B</p><h2 id="slice">2. Slice</h2><p>C</p>'
  units=chapter_units(b)
  self.assertEqual([u['title'] for u in units],['1. 基础','2. Slice'])
  self.assertIn('<p>B</p>',units[0]['content']);self.assertNotIn('Slice',units[0]['content'])
  self.assertEqual(''.join(u['content'] for u in units),b[b.index('<h2'):])
 def test_library_hides_question_splits_and_duplicate_whole_when_chapters_exist(self):
  self.assertIsNotNone(visible_documents)
  c=[{'id':'full','path':'资料源/go.html','topic':'Go','source':'小林','replaced_by_chapters':True},
     {'id':'q1','path':'学习台/data/正文分节/q.html'},
     {'id':'c1','path':'学习台/data/原文模块/c1.html','original_module':True},
     {'id':'mysql','path':'资料源/mysql.md'}]
  self.assertEqual([a['id'] for a in visible_documents(c)],['c1','mysql'])
