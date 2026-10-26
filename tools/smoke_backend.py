"""Run on each target platform against the actual frozen executable."""
from pathlib import Path
import subprocess,sys,tempfile,threading,queue,json,urllib.request,base64
exe=str(Path(sys.argv[1]).resolve())
with tempfile.TemporaryDirectory(prefix='study-package-smoke-') as t:
 root=Path(t);cmd=[exe,'--root',t,'--port','0','--no-legacy','--channel','preview'];p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 try:
  ready=queue.Queue();threading.Thread(target=lambda:ready.put(p.stdout.readline()),daemon=True).start();line=ready.get(timeout=30);assert line,(p.poll(),p.stderr.read());url=json.loads(line)['url']
  def get(route):return json.load(urllib.request.urlopen(url+route,timeout=10))
  assert get('/api/app')['channel']=='preview';assert not get('/api/setup')['ready'];assert get('/api/updates')['status']=='preview'
  req=urllib.request.Request(url+'/api/resources/import-files',data=json.dumps({'topic':'测试','files':[{'name':'试读.md','data':base64.b64encode('# 标题\n\n完整正文。'.encode()).decode()}]}).encode(),headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=10) as r:row=json.load(r)['articles'][0]
  assert '完整正文' in get('/api/article?id='+row['id'])['content']
  p2=subprocess.run(cmd,capture_output=True,timeout=15);assert p2.returncode!=0
  from pypdf import PdfWriter
  from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
  writer=PdfWriter();page=writer.add_blank_page(300,300);font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')});page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})});stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 20 250 Td (Daily Study smoke) Tj ET');page[NameObject('/Contents')]=writer._add_object(stream)
  pdf=root/'normal.pdf';writer.write(pdf);output=root/'pdf.json'
  done=subprocess.run([exe,'--extract-pdf',str(pdf),str(output)],capture_output=True,timeout=20);assert done.returncode==0,done.stderr
  assert 'Daily Study smoke' in json.loads(output.read_text(encoding='utf-8')).get('text','')
  print('Frozen '+sys.platform+' preview, lock, UTF8 reading and PDF passed')
 finally:
  p.terminate();p.wait(timeout=10)
