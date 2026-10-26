import unittest,json,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
try:from reading_context import current_section,conversation_history
except ImportError:current_section=conversation_history=None
class ContextTests(unittest.TestCase):
 def test_only_selected_html_section_and_following_subheadings(self):
  self.assertIsNotNone(current_section)
  raw='<h2>模块</h2><h3>A</h3><p>无关前文</p><h3>B</h3><p>目标选中句</p><h4>例子</h4><p>本节例子</p><h3>C</h3><p>无关后文</p>'
  c=current_section(raw,'html','目标选中句')
  self.assertEqual(c['title'],'B');self.assertIn('本节例子',c['text']);self.assertNotIn('无关前文',c['text']);self.assertNotIn('无关后文',c['text'])
 def test_section_hint_disambiguates_repeated_quote(self):
  self.assertIsNotNone(current_section)
  c=current_section('<h2>A</h2><p>同一句</p><h2>B</h2><p>同一句。第二节特有解释</p>','html','同一句',1)
  self.assertEqual(c['title'],'B');self.assertNotIn('A',c['text'])
 def test_markdown_code_fence_does_not_create_heading(self):
  self.assertIsNotNone(current_section)
  c=current_section('# 文档\n## A\n```md\n## 假标题\n```\n目标句\n## B\n不相关','markdown','目标句')
  self.assertEqual(c['title'],'A');self.assertNotIn('不相关',c['text'])
 def test_long_section_centers_on_selection(self):
  self.assertIsNotNone(current_section)
  c=current_section('<h3>长节</h3><p>'+('前'*15000)+'目标句'+('后'*15000)+'</p>','html','目标句')
  self.assertIn('目标句',c['text']);self.assertLessEqual(len(c['text']),8000);self.assertTrue(c['truncated'])
 def test_history_includes_more_than_five_complete_turns_and_limits_size(self):
  self.assertIsNotNone(conversation_history)
  rows=[{'question':f'问题{i}','reply':f'回答{i}','quote':'','section_index':i} for i in range(40)]
  h=conversation_history(rows)
  self.assertEqual(len(h),30);self.assertEqual(h[0]['question'],'问题10');self.assertEqual(h[-1]['reply'],'回答39')
  huge=[{'question':str(i),'reply':'x'*9000} for i in range(20)]
  h=conversation_history(huge);self.assertLessEqual(len(json.dumps(h,ensure_ascii=False)),40000);self.assertEqual(h[-1]['question'],'19')
