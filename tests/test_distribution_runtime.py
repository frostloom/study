import unittest,tempfile,subprocess,sys,os
from pathlib import Path
from app_info import default_data_root
from runtime_lock import FileLock,parent_alive
class RuntimeDistributionTests(unittest.TestCase):
 def test_preview_roots_never_overlap_stable_on_each_platform(self):
  home=Path('/tmp/test-home')
  for platform in ['darwin','win32']:
   a=default_data_root('stable',platform,home);b=default_data_root('preview',platform,home)
   self.assertNotEqual(a,b);self.assertFalse(a.is_relative_to(b));self.assertFalse(b.is_relative_to(a))
  with self.assertRaises(ValueError):default_data_root('unknown','darwin',home)
 def test_second_process_cannot_write_same_data_until_lock_released(self):
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'.runtime.lock';lock=FileLock(path);lock.acquire()
   script='from pathlib import Path;from runtime_lock import FileLock;import sys;x=FileLock(Path(sys.argv[1]));x.acquire();print("acquired")'
   p=subprocess.run([sys.executable,'-c',script,str(path)],capture_output=True,text=True)
   self.assertNotEqual(p.returncode,0)
   lock.close();p=subprocess.run([sys.executable,'-c',script,str(path)],capture_output=True,text=True)
   self.assertEqual(p.returncode,0,p.stderr);self.assertIn('acquired',p.stdout)
 def test_parent_exit_detected(self):
  self.assertTrue(parent_alive(os.getpid()))
  child=subprocess.Popen([sys.executable,'-c','pass']);child.wait()
  self.assertFalse(parent_alive(child.pid))
 def test_config_and_catalog_survive_non_utf8_windows_style_locale(self):
  with tempfile.TemporaryDirectory() as t:
   script="import locale,json,sys;locale.setlocale(locale.LC_CTYPE,'C');from model import ModelClient;from migration import ensure_catalog;c=ModelClient(sys.argv[1]);c.save_settings({'base_url':'https://example.com/v1','model':'\\u6a21\\u578b'});a=ensure_catalog(sys.argv[1]);assert a[0]['id']=='welcome-demo';assert c.settings()['model']=='\\u6a21\\u578b'"
   p=subprocess.run([sys.executable,'-X','utf8=0','-c',script,t],capture_output=True,env={**os.environ,'PYTHONUTF8':'0','PYTHONCOERCECLOCALE':'0'})
   self.assertEqual(p.returncode,0,p.stderr.decode('utf-8',errors='replace'))
 def test_native_preview_can_reopen_same_editable_source_without_launcher(self):
  from tools.preview import prepare_preview
  with tempfile.TemporaryDirectory() as t:
   base=Path(t);source=base/'开发源码';source.mkdir();(source/'backend_entry.py').write_text('# development',encoding='utf-8');python=base/'python';python.write_bytes(b'executable');data=base/'preview-data'
   prepare_preview(source,python,data)
   self.assertEqual((data/'.development-source').read_text(encoding='utf-8').splitlines(),[str(source.resolve()),str(python.resolve())])
   self.assertEqual(list(data.iterdir()),[data/'.development-source'])
