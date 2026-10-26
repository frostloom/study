import base64,tempfile,unittest
from pathlib import Path
from reading_context import current_section
from model import ModelClient
from unittest.mock import patch

PNG='data:image/png;base64,'+base64.b64encode(b'\x89PNG\r\n\x1a\n'+b'x'*20).decode()
class VisionTests(unittest.TestCase):
 def test_current_section_exposes_only_its_images_and_alt_text(self):
  raw='<h2>A</h2><img src="a.png" alt="other"><h2>B</h2><p>target</p><img src="b.svg" alt="target diagram"><h2>C</h2><img src="c.png">'
  s=current_section(raw,'html','target')
  self.assertEqual([(x['src'],x['alt']) for x in s['images']],[('b.svg','target diagram')])
 def test_markdown_images_inside_code_are_not_attachments(self):
  s=current_section('## A\n```md\n![fake](bad.png)\n```\n![real](good.png)','markdown')
  self.assertEqual([x['src'] for x in s['images']],['good.png'])
 def test_multimodal_generate_sends_actual_image_blocks(self):
  with tempfile.TemporaryDirectory() as t:
   m=ModelClient(t);m.save_settings({'base_url':'https://example.com/v1','model':'vision'})
   with patch.object(m,'_request',return_value='OK'):m.test_connection()
   with patch.object(m,'_request',return_value='{"reply":"seen"}') as req:
    m.generate('Explain diagram',{},images=[{'data_url':PNG,'alt':'diagram'}])
   message=req.call_args.args[1][-1]['content']
   self.assertEqual(message[0]['type'],'text');self.assertEqual(message[1]['image_url']['url'],PNG)
 def test_invalid_image_bytes_never_reach_model(self):
  with tempfile.TemporaryDirectory() as t:
   m=ModelClient(t)
   with patch.object(m,'_request') as req:
    with self.assertRaises(ValueError):m.generate('bad',{},images=[{'data_url':'data:image/png;base64,YmFk','alt':''}])
    req.assert_not_called()
 def test_local_context_resolves_svg_and_refuses_files_outside_material(self):
  from vision_context import prepare_images
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);folder=root/'资料源/Book';folder.mkdir(parents=True);(folder/'fig.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>')
   (root/'secret.png').write_bytes(b'\x89PNG\r\n\x1a\n'+b'x'*20)
   a={'path':'资料源/Book/a.md','source_url':''}
   result=prepare_images(root,a,[{'src':'fig.svg','alt':'diagram'}]);self.assertEqual(len(result['images']),1);self.assertTrue(result['images'][0]['data_url'].startswith('data:image/svg+xml;base64,'))
   result=prepare_images(root,a,[{'src':'../../secret.png','alt':''}]);self.assertEqual(result['images'],[]);self.assertTrue(result['warnings'])

class AskVisionTests(unittest.TestCase):
 def test_prepared_section_and_images_are_sent_and_audited(self):
  from learning import Learning
  from store import Store
  from vision_context import source_id
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);raw='<h2>A</h2><p>Do not include</p><h2>B</h2><p>Target text</p><img src="'+PNG+'" alt="Diagram B">';(root/'a.html').write_text(raw)
   s=Store(root,[dict(id='a',title='Book',path='a.html',format='html',source_url='',topic='Agent')])
   class M:
    def generate(inner,prompt,schema=None,images=None):inner.prompt=prompt;inner.images=images;return {'reply':'Seen'}
   model=M();l=Learning(s,model);p=l.prepare_context('a','Target text',1)
   self.assertEqual(p['section_title'],'B');self.assertEqual(len(p['images']),1)
   result=l.ask('a','Explain','Target text',1,images=[{'data_url':PNG,'source_id':source_id(PNG)}])
   self.assertEqual(len(model.images),1);self.assertNotIn('Do not include',model.prompt)
   self.assertEqual(result['context']['image_count'],1);self.assertEqual(s.chats(article_id='a')[0]['context']['section_title'],'B')
   with self.assertRaises(ValueError):l.ask('a','Explain','Target text',1,images=[])
   with self.assertRaises(ValueError):l.ask('a','Explain','Target text',1,images=[{'data_url':PNG,'source_id':'other'}])
 def test_explicit_text_only_does_not_claim_to_see_images(self):
  from learning import Learning
  from store import Store
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'a.html').write_text('<h2>A</h2><p>Text</p><img src="'+PNG+'">')
   s=Store(root,[dict(id='a',title='Book',path='a.html',format='html',source_url='',topic='Agent')])
   class M:
    def generate(inner,prompt,schema=None):inner.prompt=prompt;return {'reply':'Text only'}
   m=M();result=Learning(s,m).ask('a','Explain',text_only=True)
   self.assertIn('未附图片',m.prompt);self.assertEqual(result['context']['image_count'],0);self.assertTrue(result['context']['text_only'])

class MarkdownVisionTests(unittest.TestCase):
 def test_reference_and_raw_html_images_use_the_same_section(self):
  raw='## A\n![before](a.png)\n## B\nTarget\n![chart][figure]\n<img src="inline.svg" alt="html diagram">\n## C\n![after](c.png)\n[figure]: reference.png "title"'
  s=current_section(raw,'markdown','Target')
  self.assertEqual([x['src'] for x in s['images']],['reference.png','inline.svg'])
 def test_inline_code_and_escaped_image_examples_are_not_images(self):
  raw='## A\n`![example](fake.png)`\n\\![escaped](fake2.png)\n![real](real.png)'
  self.assertEqual([x['src'] for x in current_section(raw,'markdown')['images']],['real.png'])

class InlineSVGTests(unittest.TestCase):
 def test_inline_svg_is_attached_only_for_current_section(self):
  raw='<h2>A</h2><svg viewBox="0 0 100 50"><text x="5" y="20">Hidden</text></svg><h2>B</h2><p>Target</p><svg viewBox="0 0 800 400" aria-label="Timeline"><text x="5" y="20">A commits</text></svg>'
  s=current_section(raw,'html','Target')
  self.assertEqual(len(s['images']),1)
  encoded=s['images'][0]['src'].split(',',1)[1];svg=base64.b64decode(encoded).decode()
  self.assertIn('xmlns="http://www.w3.org/2000/svg"',svg);self.assertIn('A commits',svg);self.assertNotIn('Hidden',svg)
  self.assertEqual(s['images'][0]['alt'],'Timeline')
