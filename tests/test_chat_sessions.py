import unittest,tempfile,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from store import Store
from learning import Learning
class SessionsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'a.html').write_text('<h3>A</h3><p>当前小节原文</p>',encoding='utf-8')
  self.c=[dict(id=x,title=x,topic='Go',path='a.html',source_url='https://example.com',format='html') for x in ['a','b']];self.s=Store(self.root,self.c)
 def tearDown(self):self.tmp.cleanup()
 def test_new_session_is_empty_and_history_survives_restart(self):
  old=self.s.add_chat('a','原问题','原答案');new=self.s.new_chat_session('a')
  self.assertEqual(self.s.chats(article_id='a',session_id=new['id']),[])
  fresh=Store(self.root,self.c)
  self.assertEqual(fresh.chats(article_id='a',session_id=old['session_id'])[0]['reply'],'原答案')
  self.assertEqual(len(fresh.chat_sessions('a')),2)
 def test_legacy_rows_migrate_without_losing_content(self):
  with self.s.connect() as db:db.execute('INSERT INTO conversations(day,article_id,body,created) VALUES (?,?,?,?)',('2026-10-25','a',json.dumps(dict(question='旧问题',reply='旧答案',quote='',created='2026-10-25')),'2026-10-25'))
  fresh=Store(self.root,self.c);rows=fresh.chats(article_id='a')
  self.assertEqual(rows[0]['reply'],'旧答案');self.assertTrue(rows[0]['session_id']);self.assertEqual(fresh.chat_sessions('a')[0]['count'],1)
 def test_foreign_session_is_rejected(self):
  session=self.s.new_chat_session('a')
  with self.assertRaises(ValueError):self.s.add_chat('b','问题','答案',session_id=session['id'])
 def test_new_session_prompt_does_not_include_old_answers(self):
  old=self.s.add_chat('a','旧会话独有问题','旧会话独有回答');new=self.s.new_chat_session('a')
  class M:
   def generate(inner,prompt,schema=None):inner.prompt=prompt;return {'reply':'新回答'}
  m=M();result=Learning(self.s,m).ask('a','新问题',session_id=new['id'])
  self.assertNotIn('旧会话独有',m.prompt);self.assertEqual(result['session_id'],new['id'])
  self.assertEqual(len(self.s.chats(article_id='a',session_id=old['session_id'])),1)
 def test_inflight_reply_stays_in_original_session(self):
  old=self.s.new_chat_session('a');s=self.s
  class M:
   def generate(inner,prompt,schema=None):inner.new=s.new_chat_session('a');return {'reply':'旧请求的回答'}
  m=M();result=Learning(s,m).ask('a','还未返回的问题',session_id=old['id'])
  self.assertEqual(result['session_id'],old['id']);self.assertEqual(s.chats(article_id='a',session_id=m.new['id']),[])
