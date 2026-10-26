"""Local controlled compatible API for release QA, never distributed with personal data."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import json,re
class H(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_POST(self):
  p=json.loads(self.rfile.read(int(self.headers['Content-Length'])));prompt=p['messages'][-1]['content'];output='OK'
  if '仅回复 OK' in prompt or '只回复 OK' in prompt:pass
  elif '公共网页搜索关键词' in prompt:output=json.dumps({'queries':['Python official tutorial']})
  elif 'rankings' in prompt and '搜索结果：' in prompt:
   rows=json.JSONDecoder().raw_decode(prompt.split('搜索结果：',1)[1])[0];output=json.dumps({'rankings':[{'id':r['id'],'reason':'公开来源，与当前目标相关，可先阅读基础内容。','level':'beginner'} for r in rows[:3]]},ensure_ascii=False)
  elif '候选：' in prompt:
   rows=json.JSONDecoder().raw_decode(prompt.split('候选：',1)[1])[0];match=re.search(r'阅读(\d+)分钟',prompt);budget=int(match[1]) if match else 60;tasks=[]
   for r in rows[:3]:
    if budget<=0:break
    n=min(r['minutes'],budget);tasks.append(dict(article_id=r['id'],minutes=n,scope='阅读当前模块的第一小节' if n<r['minutes'] else '完整阅读本模块'));budget-=n
   output=json.dumps({'tasks':tasks,'note':'根据选定主题和时间预算，先读当前基础内容。'},ensure_ascii=False)
  elif 'questions' in prompt and '生成中文晚间' in prompt:
   rows=json.JSONDecoder().raw_decode(prompt[prompt.find('[{'):])[0];output=json.dumps({'questions':[{'question':'请解释本次阅读的核心概念并举例。','article_ids':[rows[0]['id']],'reference_answer':'说明核心原理。','criteria':'能说明原因与例子'}]},ensure_ascii=False)
  elif 'score' in prompt and '用户回答：' in prompt:output=json.dumps({'score':2,'feedback':'验收反馈：主线清楚，可补充边界。','follow_up':'有哪些边界条件？','reference_answer':'说明原理与适用条件。'},ensure_ascii=False)
  else:output=json.dumps({'reply':'这是隔离模型验收回答：结合当前小节解释核心概念。'},ensure_ascii=False)
  raw=json.dumps({'choices':[{'message':{'role':'assistant','content':output}}]},ensure_ascii=False).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
print('QA compatible provider http://127.0.0.1:8999/v1',flush=True);ThreadingHTTPServer(('127.0.0.1',8999),H).serve_forever()
