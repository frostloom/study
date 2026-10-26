import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

try:
    from server import make_server
except ImportError:
    make_server=None

class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        (self.root/'资料源').mkdir();(self.root/'资料源/whole.md').write_text('# 完整文章\n\n开头\n\n## 第二部分\n\n结尾',encoding='utf-8')
        self.catalog=[dict(id='whole',topic='Go',title='完整正文',minutes=30,path='资料源/whole.md',source_url='https://example.com/whole')]
    def tearDown(self):
        if hasattr(self,'httpd'):self.httpd.shutdown();self.httpd.server_close();self.thread.join()
        self.tmp.cleanup()
    def start(self):
        self.assertIsNotNone(make_server,'尚未实现本地学习台服务')
        self.httpd=make_server(self.root,self.catalog,0)
        self.thread=threading.Thread(target=self.httpd.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.httpd.server_port}'
    def request(self,path,payload=None,origin=None):
        headers={}
        if payload is not None:headers['Content-Type']='application/json'
        if origin:headers['Origin']=origin
        req=urllib.request.Request(self.base+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
        with urllib.request.urlopen(req) as r:return json.load(r)
    def test_full_article_and_durable_checkbox_api(self):
        self.start()
        content=self.request('/api/article?id=whole')
        self.assertIn('第二部分',content['content']);self.assertIn('结尾',content['content'])
        self.httpd.store.generate_plan('2026-10-26')
        self.request('/api/check',{'date':'2026-10-26','article_id':'whole','done':True},self.base)
        self.assertEqual(self.request('/api/handoff?date=2026-10-26')['completed'][0]['id'],'whole')
    def test_arbitrary_files_and_cross_origin_mutation_rejected(self):
        self.start();self.httpd.store.generate_plan('2026-10-26')
        for path in ['/api/article?id=../../etc/passwd','/api/file?path=/etc/passwd']:
            with self.assertRaises(urllib.error.HTTPError) as cm:self.request(path)
            self.assertIn(cm.exception.code,[400,404])
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.request('/api/check',{'date':'2026-10-26','article_id':'whole','done':True},'https://evil.example')
        self.assertEqual(cm.exception.code,403)
        self.assertEqual(self.request('/api/handoff?date=2026-10-26')['completed'],[])

    def test_backup_contains_learning_data_without_runtime_or_webview_files(self):
        self.start()
        (self.root/'.runtime.lock').write_bytes(b'locked runtime')
        (self.root/'.server-info.json').write_text('{}',encoding='utf-8')
        webview=self.root/'WebView2';webview.mkdir();(webview/'locked-cache').write_bytes(b'cache')
        result=self.request('/api/data/backup',{})
        import zipfile
        with zipfile.ZipFile(result['path']) as z:
            names=z.namelist()
            self.assertIn('学习台/data/study.sqlite3',names)
            self.assertNotIn('.runtime.lock',names)
            self.assertNotIn('.server-info.json',names)
            self.assertFalse(any(x.startswith('WebView2/') for x in names))
