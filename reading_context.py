"""Bounded section context and complete recent question/answer pairs."""
import json,re
from html import unescape
from html.parser import HTMLParser

class Text(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.parts=[];self.skip=0
 def handle_starttag(self,t,a):
  if t in ['script','style']:self.skip+=1
  if not self.skip and t in ['p','div','li','br','pre','h1','h2','h3','h4','h5','h6']:self.parts.append('\n')
 def handle_endtag(self,t):
  if t in ['script','style']:self.skip=max(0,self.skip-1)
  if not self.skip and t in ['p','div','li','pre','h1','h2','h3','h4','h5','h6']:self.parts.append('\n')
 def handle_data(self,d):
  if not self.skip:self.parts.append(d)
def readable(raw,fmt):
 if fmt!='html':return raw.strip()
 p=Text();p.feed(raw);return re.sub(r'\n{3,}','\n\n',''.join(p.parts)).strip()
def compact(s):return re.sub(r'\s+','',''.join(s))
def headings(raw,fmt):
 if fmt=='html':return [dict(start=m.start(),level=int(m[1]),title=readable(m[2],fmt).lstrip('# ').strip()) for m in re.finditer(r'<h([1-6])\b[^>]*>(.*?)</h\1>',raw,re.S|re.I)]
 result=[];fence=None;offset=0
 for line in raw.splitlines(keepends=True):
  f=re.match(r'^ {0,3}(`{3,}|~{3,})',line)
  if f:
   token=f[1]
   if fence is None:fence=token
   elif token[0]==fence[0] and len(token)>=len(fence):fence=None
  elif fence is None:
   m=re.match(r'^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$',line)
   if m:result.append(dict(start=offset,level=len(m[1]),title=m[2].strip()))
  offset+=len(line)
 return result

def current_section(raw,fmt='markdown',quote='',section_index=None):
 hs=headings(raw,fmt)
 if section_index is not None and (type(section_index) is not int or section_index<0):raise ValueError('小节位置无效')
 sections=[]
 for i,h in enumerate(hs):
  end=next((x['start'] for x in hs[i+1:] if x['level']<=h['level']),len(raw))
  sections.append(dict(index=i,title=h['title'],text=readable(raw[h['start']:end],fmt),level=h['level']))
 normalized=compact(quote)
 match=lambda s:bool(normalized) and normalized in compact(s['text'])
 chosen=sections[section_index] if section_index is not None and section_index<len(sections) else None
 if normalized and (chosen is None or not match(chosen)):
  matches=[s for s in sections if match(s)]
  if matches:chosen=max(matches,key=lambda s:s['level'])
 if chosen is None:
  # A standalone H1 is normally a document wrapper, not the reading subsection.
  chosen=next((s for s in sections if s['level']>=2),sections[0] if sections else dict(index=None,title='无标题小节',text=readable(raw,fmt)))
 text=chosen['text'];truncated=len(text)>8000
 if truncated:
  start=0
  if normalized:
   chars=[];positions=[]
   for i,ch in enumerate(text):
    if not ch.isspace():chars.append(ch);positions.append(i)
   at=''.join(chars).find(normalized)
   if at>=0:start=max(0,min(positions[at]-2000,len(text)-8000))
  text=text[start:start+8000]
 return dict(index=chosen['index'],title=chosen['title'],text=text,truncated=truncated)

def conversation_history(rows,max_turns=30,max_chars=40000):
 selected=[]
 for row in reversed(rows[-max_turns:]):
  item={k:row[k] for k in ['question','reply','quote','section_index','section_title'] if k in row}
  if len(json.dumps([item]+selected,ensure_ascii=False))>max_chars:
   if not selected:
    # An unusually large latest reply must not erase the latest user question.
    item['question']=str(item.get('question',''))[:6000];item['reply']=str(item.get('reply',''))[-24000:];item['quote']=str(item.get('quote',''))[:8000];item['history_truncated']=True
    while len(json.dumps([item],ensure_ascii=False))>max_chars:item['reply']=item['reply'][1000:]
    selected=[item]
   break
  selected.insert(0,item)
 return selected
