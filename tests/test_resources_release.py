import base64
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from store import Store


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.rows = [{'id':'old','title':'Existing','path':'old.md'}]
        self.store = Store(self.root,self.rows)
        from resources import ResourceLibrary
        self.lib = ResourceLibrary(self.root,self.rows,self.store,None)
    def tearDown(self):
        self.tmp.cleanup()
    def file(self,name,data):
        return {'name':name,'data':base64.b64encode(data).decode()}
    def test_import_preserves_catalog_and_contains_paths(self):
        result=self.lib.import_files([self.file('../../idea.md',b'# My lesson\nComplete text')],'Python')
        self.assertEqual(self.rows[0]['id'],'old')
        row=result[0]
        self.assertEqual(row['title'],'My lesson')
        self.assertTrue(row['learning_unit'])
        self.assertEqual(row['format'],'markdown')
        self.assertEqual(self.store.catalog[row['id']],row)
        self.assertIn('Complete text',(self.root/row['path']).read_text(encoding='utf-8'))
        self.assertTrue((self.root/row['path']).resolve().is_relative_to(self.root))
        persisted=json.loads((self.store.data/'catalog.json').read_text(encoding='utf-8'))
        self.assertEqual([r['id'] for r in persisted],['old',row['id']])
    def test_invalid_batch_does_not_add_rows(self):
        with self.assertRaises(ValueError):
            self.lib.import_files([self.file('a.txt',b'Hello'),self.file('bad.exe',b'bad')],'General')
        self.assertEqual(len(self.rows),1)
    def test_html_is_sanitized_and_docx_text_extracted(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:
            z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Document lesson</w:t></w:r></w:p></w:body></w:document>')
        result=self.lib.import_files([self.file('web.html',b'<h1>Safe lesson</h1><script>alert(1)</script><p onclick="bad()">Main body</p>'),self.file('word.docx',b.getvalue())],'General')
        html=(self.root/result[0]['path']).read_text(encoding='utf-8')
        self.assertIn('Main body',html)
        self.assertNotIn('alert',html)
        self.assertNotIn('onclick',html)
        self.assertIn('Document lesson',(self.root/result[1]['path']).read_text(encoding='utf-8'))
    def test_discovery_grounds_model_ids_in_search_results(self):
        class Model:
            def generate(self,prompt,schema):
                if 'queries' in schema.get('properties',{}):return {'queries':['Python official tutorial']}
                return {'rankings':[{'id':'invented','reason':'bad'},{'id':'s1','reason':'Official introduction','level':'beginner','url':'https://evil.invalid'}]}
        self.lib.model=Model()
        with patch('resources.validate_url',return_value=('https','docs.python.org',443,'/3/tutorial/',['151.101.0.223'])), patch('resources.search_public',return_value=[{'title':'Python tutorial','url':'https://docs.python.org/3/tutorial/','snippet':'Learn Python'}]):
            result=self.lib.discover({'topics':['Python'],'level':'beginner'})
        self.assertEqual(result['candidates'][0]['url'],'https://docs.python.org/3/tutorial/')
        self.assertEqual(len(result['candidates']),1)
        self.assertEqual(len(self.rows),1)


class SafeWebTests(unittest.TestCase):
    def test_rejects_private_mixed_dns_and_credentials(self):
        from safe_web import validate_url
        for url in ['file:///etc/passwd','http://127.0.0.1/','http://169.254.169.254/','http://[::1]/','https://user:secret@example.com/','http://localhost/']:
            with self.subTest(url=url),self.assertRaises(ValueError):validate_url(url)
        dns=[(2,1,6,'',('93.184.216.34',443)),(2,1,6,'',('10.0.0.1',443))]
        with patch('safe_web.socket.getaddrinfo',return_value=dns), self.assertRaises(ValueError):validate_url('https://example.com/')
    def test_redirect_is_validated_before_connect(self):
        from safe_web import fetch_public
        class Reply:
            status=302
            def getheader(self,name,default=None):return 'http://127.0.0.1/private' if name=='Location' else default
            def read(self,n):return b''
        with patch('safe_web.validate_url',side_effect=[('https','example.com',443,'/',['93.184.216.34']),ValueError('private')]),patch('safe_web._request',return_value=(Reply(),lambda:None)):
            with self.assertRaises(ValueError):fetch_public('https://example.com/')

class ResourceBoundaryTests(ResourceTests):
    def test_oversized_file_and_corrupt_zip_leave_catalog_intact(self):
        with self.assertRaises(ValueError):self.lib.import_files([self.file('huge.txt',b'a'*(8*1024*1024+1))],'General')
        with self.assertRaises(ValueError):self.lib.import_files([self.file('broken.docx',b'not zip')],'General')
        self.assertEqual(len(self.rows),1)
    def test_catalog_write_failure_leaves_memory_and_old_catalog(self):
        path=self.store.data/'catalog.json';path.write_text(json.dumps(self.rows),encoding='utf-8')
        with patch('resources.os.replace',side_effect=OSError('disk full')),self.assertRaises(OSError):
            self.lib.import_files([self.file('lesson.txt',b'Complete lesson')],'General')
        self.assertEqual([x['id'] for x in self.rows],['old'])
        self.assertEqual(list(self.store.catalog),['old'])
        self.assertEqual(json.loads(path.read_text(encoding='utf-8'))[0]['id'],'old')
        self.assertEqual(list((self.root/'学习台/imports').iterdir()),[])
    def test_pdf_extracts_actual_text_and_rejects_scanned_document(self):
        try:
            from pypdf import PdfWriter
            from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
        except ImportError:self.skipTest('pypdf available in release build environment')
        writer=PdfWriter();page=writer.add_blank_page(300,300)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
        stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 10 200 Td (A real PDF lesson) Tj ET')
        page[NameObject('/Contents')]=stream
        content=io.BytesIO();writer.write(content)
        row=self.lib.import_files([self.file('paper.pdf',content.getvalue())],'General')[0]
        self.assertIn('A real PDF lesson',(self.root/row['path']).read_text(encoding='utf-8'))
        blank=PdfWriter();blank.add_blank_page(300,300);output=io.BytesIO();blank.write(output)
        with self.assertRaises(ValueError):self.lib.import_files([self.file('scanned.pdf',output.getvalue())],'General')
    def test_url_import_keeps_final_source_and_escapes_active_html(self):
        with patch('resources.fetch_public',return_value={'url':'https://example.com/lesson','data':b'<title>Web Lesson</title><h1>Topic</h1><script>malicious()</script><p>Full body</p>','content_type':'text/html'}):
            row=self.lib.import_url('https://example.com/start','General')
        self.assertEqual(row['source_url'],'https://example.com/lesson')
        self.assertEqual(row['title'],'Web Lesson')
        self.assertNotIn('malicious',(self.root/row['path']).read_text(encoding='utf-8'))


class FetchBoundaryTests(unittest.TestCase):
    def test_response_byte_limit(self):
        from safe_web import fetch_public
        class Reply:
            status=200
            def getheader(self,name,default=None):return default
            def read(self,n):return b'x'*n
        with patch('safe_web.validate_url',return_value=('https','example.com',443,'/',['93.184.216.34'])),patch('safe_web._request',return_value=(Reply(),lambda:None)):
            with self.assertRaises(ValueError):fetch_public('https://example.com/',max_bytes=30)
    def test_body_uses_single_socket_reads_to_enforce_elapsed_deadline(self):
        from safe_web import fetch_public
        class Reply:
            status=200
            def getheader(self,name,default=None):return default
            def read(self,n):raise AssertionError('Buffered read may wait indefinitely for a slow dripping response')
            def read1(self,n):return b'one chunk'
        with patch('safe_web.time.monotonic',side_effect=[0,0,0,0,20]),patch('safe_web.validate_url',return_value=('https','example.com',443,'/',['93.184.216.34'])),patch('safe_web._request',return_value=(Reply(),lambda:None)):
            with self.assertRaisesRegex(ValueError,'超时'):fetch_public('https://example.com/',timeout=12)
    def test_actual_dripping_headers_cannot_extend_request_deadline(self):
        import socket
        import threading
        import time
        from safe_web import fetch_public
        client,server=socket.socketpair()
        stop=threading.Event()
        def drip():
            try:
                server.recv(8192)
                for byte in b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\nContent-Type: text/plain\r\n\r\nok':
                    if stop.wait(0.02):break
                    server.sendall(bytes([byte]))
            except OSError:pass
            finally:server.close()
        worker=threading.Thread(target=drip,daemon=True);worker.start()
        started=time.monotonic()
        try:
            with patch('safe_web.validate_url',return_value=('http','public.example',80,'/',['93.184.216.34'])),patch('safe_web.socket.create_connection',return_value=client):
                with self.assertRaises(ValueError):fetch_public('http://public.example/',timeout=0.15)
            self.assertLess(time.monotonic()-started,0.7,'Byte progress must not reset the whole request deadline')
        finally:
            stop.set();client.close();worker.join(timeout=1)
    def test_actual_truncated_content_length_is_rejected(self):
        import socket
        import threading
        from safe_web import fetch_public
        client,server=socket.socketpair()
        def truncated():
            try:
                server.recv(8192)
                server.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\nabc')
            finally:server.close()
        worker=threading.Thread(target=truncated,daemon=True);worker.start()
        try:
            with patch('safe_web.validate_url',return_value=('http','public.example',80,'/',['93.184.216.34'])),patch('safe_web.socket.create_connection',return_value=client):
                with self.assertRaisesRegex(ValueError,'完整|中断'):fetch_public('http://public.example/',timeout=1)
        finally:client.close();worker.join(timeout=1)

class PDFIsolationTests(unittest.TestCase):
    def test_small_compressed_pdf_cannot_expand_aggregate_stream_budget(self):
        try:
            from pypdf import PdfWriter
            from pypdf.generic import NameObject,DecodedStreamObject,DictionaryObject
        except ImportError:self.skipTest('pypdf required')
        from resources import extract_document
        writer=PdfWriter()
        for _ in range(6):
            page=writer.add_blank_page(300,300)
            page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})})})
            stream=DecodedStreamObject();stream.set_data(b' '*(2*1024*1024)+b'BT /F1 12 Tf 10 200 Td (lesson) Tj ET')
            page[NameObject('/Contents')]=stream.flate_encode()
        content=io.BytesIO();writer.write(content)
        self.assertLess(len(content.getvalue()),30000)
        with self.assertRaisesRegex(ValueError,'预算|过大|限制'):
            extract_document('compressed.pdf',content.getvalue())
    def test_pdf_timeout_is_reported_without_importing_partial_text(self):
        import subprocess
        from resources import extract_document
        with patch('resources.subprocess.run',side_effect=subprocess.TimeoutExpired(['owned-pdf-child'],15)):
            with self.assertRaisesRegex(ValueError,'超时'):extract_document('paper.pdf',b'%PDF-1.4')

class BatchContractTests(ResourceTests):
    def test_seven_files_are_rejected_before_catalog_changes(self):
        with self.assertRaises(ValueError):
            self.lib.import_files([self.file('lesson.txt',b'Valid complete lesson') for _ in range(7)],'General')
        self.assertEqual(len(self.rows),1)

class PreviewTests(ResourceTests):
    def test_preview_shows_real_content_without_import_or_catalog_changes(self):
        with patch('resources.fetch_public',return_value={'url':'https://example.com/final','data':b'<title>Real Lesson</title><p>Actual article content.</p><script>bad()</script>','content_type':'text/html'}):
            result=self.lib.preview_url('https://example.com/start')
        self.assertEqual(result,{'title':'Real Lesson','url':'https://example.com/final','text':'Actual article content.','truncated':False})
        self.assertEqual(len(self.rows),1)
        self.assertEqual(list(self.store.catalog),['old'])
        self.assertFalse((self.store.data/'catalog.json').exists())
        self.assertEqual(list(self.lib.imports.iterdir()),[])
    def test_preview_limits_display_text_and_reports_truncation(self):
        with patch('resources.fetch_public',return_value={'url':'https://example.com/long.txt','data':b'a'*16001,'content_type':'text/plain'}):
            result=self.lib.preview_url('https://example.com/long.txt')
        self.assertEqual(result['text'],'a'*16000)
        self.assertTrue(result['truncated'])
        self.assertEqual(len(self.rows),1)
    def test_preview_rejects_private_network_target_without_persisting(self):
        with self.assertRaises(ValueError):self.lib.preview_url('http://127.0.0.1/private')
        self.assertEqual(len(self.rows),1)
        self.assertEqual(list(self.lib.imports.iterdir()),[])

class HeadingStructureTests(unittest.TestCase):
    def test_html_heading_levels_preserve_target_section_context(self):
        from resources import extract_document
        from reading_context import current_section
        _,text=extract_document('lesson.html',b'<h1>Guide</h1><h2>First</h2><p>First topic body.</p><h2>Second</h2><p>Target topic body.</p><h6>Detail</h6><p>Target detail.</p>')
        self.assertIn('# Guide',text)
        self.assertIn('## First',text)
        self.assertIn('## Second',text)
        self.assertIn('###### Detail',text)
        context=current_section(text,'markdown','Target topic body.')
        self.assertEqual(context['title'],'Second')
        self.assertIn('Target detail.',context['text'])
        self.assertNotIn('First topic body.',context['text'])
    def test_docx_heading_styles_preserve_target_section_context(self):
        from resources import extract_document
        from reading_context import current_section
        xml='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Guide</w:t></w:r></w:p><w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>First</w:t></w:r></w:p><w:p><w:r><w:t>First topic body.</w:t></w:r></w:p><w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>Second</w:t></w:r></w:p><w:p><w:r><w:t>Target topic body.</w:t></w:r></w:p></w:body></w:document>'
        content=io.BytesIO()
        with zipfile.ZipFile(content,'w') as archive:archive.writestr('word/document.xml',xml)
        _,text=extract_document('lesson.docx',content.getvalue())
        self.assertIn('# Guide',text)
        self.assertIn('## Second',text)
        context=current_section(text,'markdown','Target topic body.')
        self.assertEqual(context['title'],'Second')
        self.assertNotIn('First topic body.',context['text'])

class SemanticHTMLTests(unittest.TestCase):
    def test_semantic_main_excludes_surrounding_navigation_and_footer(self):
        from resources import extract_document
        markup=b'<html><head><title>Official lesson</title></head><body><header>Global account links</header><nav>Menu navigation</nav><main role="main"><h1>Learning guide</h1><article><h2>Real section</h2><p>Full substantive lesson text.</p></article></main><footer>Legal boilerplate</footer></body></html>'
        title,text=extract_document('lesson.html',markup)
        self.assertEqual(title,'Official lesson')
        self.assertIn('# Learning guide',text)
        self.assertIn('## Real section',text)
        self.assertIn('Full substantive lesson text.',text)
        self.assertNotIn('Menu navigation',text)
        self.assertNotIn('Global account links',text)
        self.assertNotIn('Legal boilerplate',text)
    def test_nonsemantic_body_preserves_content_with_only_chrome_removed(self):
        from resources import extract_document
        markup=b'<title>Plain lesson</title><body><header>Top site links</header><div><h1>Document</h1><p>Opening body</p><div><h2>Details</h2><p>All details retained</p></div></div><aside>Ads</aside><form>Newsletter signup</form><nav>Next pages</nav><footer>Contact links</footer></body>'
        title,text=extract_document('plain.html',markup)
        self.assertEqual(title,'Plain lesson')
        self.assertIn('# Document',text)
        self.assertIn('Opening body',text)
        self.assertIn('All details retained',text)
        for noise in ['Top site links','Ads','Newsletter signup','Next pages','Contact links']:self.assertNotIn(noise,text)
