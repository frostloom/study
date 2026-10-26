import sys,tempfile,unittest,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from store import Store
from learning import Learning
class Capture:
 def __init__(self):self.prompts=[]
 def generate(self,prompt,schema=None):self.prompts.append(prompt);return {'reply':'回答'}
class AskContextTests(unittest.TestCase):
 def test_followup_keeps_section_and_includes_older_conversation(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);(r/'a.html').write_text('<h2>模块</h2><h3>A</h3><p>不应附带的A节原文</p><h3>B</h3><p>选中目标</p>',encoding='utf-8')
   c=[dict(id='a',title='文档',topic='Go',path='a.html',source_url='https://example.com',format='html')];s=Store(r,c);m=Capture();e=Learning(s,m)
   for i in range(15):s.add_chat('a',f'历史问题{i}',f'历史回答{i}')
   first=e.ask('a','解释','选中目标',section_index=2)
   self.assertEqual(first['section_index'],2)
   second=e.ask('a','那它为什么这样？')
   self.assertEqual(second['section_index'],2)
   self.assertNotIn('不应附带的A节原文',m.prompts[-1]);self.assertIn('历史问题0',m.prompts[-1]);self.assertIn('选中目标',m.prompts[-1])
