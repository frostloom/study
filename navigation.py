"""Original-document navigation; legacy question records remain for old history."""
import re
from html import unescape

def chapter_units(body):
 heads=list(re.finditer(r'<h2\b([^>]*)>(.*?)</h2>',body,re.S));result=[]
 for i,h in enumerate(heads):
  anchor=re.search(r'\bid="([^"]+)"',h[1]);end=heads[i+1].start() if i+1<len(heads) else len(body)
  result.append(dict(title=unescape(re.sub('<[^>]+>','',h[2])).lstrip('# ').strip(),anchor=anchor[1] if anchor else str(i),content=body[h.start():end],order=i))
 return result

def visible_documents(catalog):
 return [a for a in catalog if a.get('original_module') or (a['path'].startswith('资料源/') and not a.get('replaced_by_chapters'))]
