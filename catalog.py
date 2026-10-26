"""Complete document indexing: article bodies are never replaced by summaries."""
from html import unescape
from html.parser import HTMLParser
import hashlib
import math
from pathlib import Path
import re


def plain(content):
    return unescape(re.sub('<[^>]+>', '', content)).strip()


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.depth=0; self.output=[];self.found=False
    def handle_starttag(self,tag,attrs):
        if not self.depth:
            if tag=='div' and 'theme-default-content' in dict(attrs).get('class','').split():
                self.depth=1;self.found=True
            return
        if tag=='div': self.depth+=1
        self.output.append(self.get_starttag_text())
    def handle_endtag(self,tag):
        if not self.depth:return
        if tag=='div':self.depth-=1
        if self.depth:self.output.append(f'</{tag}>')
    def handle_data(self,data):
        if self.depth:self.output.append(data)
    def handle_entityref(self,name):
        if self.depth:self.output.append(f'&{name};')
    def handle_charref(self,name):
        if self.depth:self.output.append(f'&#{name};')
    def handle_startendtag(self,tag,attrs):
        if self.depth:self.output.append(self.get_starttag_text())


def extract_article(html):
    p=ArticleParser();p.feed(html)
    if not p.found or not ''.join(p.output).strip():raise ValueError('未找到完整正文容器')
    return ''.join(p.output)


def split_html_questions(body):
    heads=list(re.finditer(r'<h([23])\b[^>]*\bid="([^"]+)"[^>]*>(.*?)</h\1>',body,re.S))
    questions=[];chapter=''
    for i,h in enumerate(heads):
        if h[1]=='2':chapter=plain(h[3]).replace('#','').strip();continue
        end=heads[i+1].start() if i+1<len(heads) else len(body)
        questions.append(dict(anchor=h[2],title=plain(h[3]).replace('#','').strip(),chapter=chapter,content=body[h.start():end]))
    return questions


def estimate(content):
    # Reading + interpreting interview notes; not a hard stopwatch or a mastery score.
    text=plain(content)
    chars=len(re.findall(r'[\u3400-\u9fff]',text));words=len(re.findall(r'\b[A-Za-z][\w-]*\b',text))
    return max(8, min(120, int(math.ceil((chars/230+words/140)*1.35/5)*5)))


def stable_id(key):return hashlib.sha256(key.encode()).hexdigest()[:18]


def markdown_title(content,fallback):
    m=re.search(r'^#{1,2}\s+(.+)',content,re.M)
    if m:return re.sub(r'\s*\{.*?\}\s*$','',m[1]).strip()
    m=re.search(r'^title:\s*[\"\']?(.+?)[\"\']?$',content,re.M)
    return m[1] if m else fallback


def split_markdown(content, max_chars=6500):
    """Split long complete documents on headings, without dropping any text."""
    if len(content)<max_chars:return [('全文',content)]
    matches=list(re.finditer(r'^#{2,3}\s+(.+)$',content,re.M))
    if len(matches)<2:return [('全文',content)]
    chunks=[]
    if content[:matches[0].start()].strip():chunks.append(('导读',content[:matches[0].start()]))
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(content)
        chunks.append((m[1].strip(),content[m.start():end]))
    return chunks
