import tempfile,unittest,json,os
from pathlib import Path
from unittest.mock import patch
from model import ModelClient
class Response:
 def __init__(self,obj):self.data=json.dumps(obj).encode()
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def read(self,n=-1):return self.data
class ModelAPIReleaseTests(unittest.TestCase):
 def test_api_is_only_provider_and_key_not_public(self):
  with tempfile.TemporaryDirectory() as t:
   m=ModelClient(t);self.assertEqual(m.settings()['provider'],'api')
   m.save_settings({'base_url':'https://example.com/v1','model':'test','api_key':'private-secret'})
   self.assertNotIn('private-secret',json.dumps(m.public_settings()));self.assertFalse(m.public_settings()['ready'])
   if os.name!='nt':self.assertEqual(os.stat(m.config_path).st_mode&0o777,0o600)
 def test_changed_endpoint_clears_old_key_and_verification(self):
  with tempfile.TemporaryDirectory() as t:
   m=ModelClient(t);m.save_settings({'base_url':'https://example.com/v1','model':'x','api_key':'s'})
   m.save_settings({'base_url':'https://other.example/v1','api_key':''});self.assertEqual(m.settings()['api_key'],'');self.assertFalse(m.public_settings()['ready'])
 def test_validated_connection_and_structured_generate(self):
  with tempfile.TemporaryDirectory() as t:
   m=ModelClient(t);m.save_settings({'base_url':'http://127.0.0.1:9000/v1','model':'x'})
   with patch.object(m,'_request',return_value='OK'):self.assertTrue(m.test_connection()['ok'])
   self.assertTrue(m.public_settings()['ready'])
   with patch.object(m,'_request',return_value='```json\n{"reply":"hello"}\n```'):
    self.assertEqual(m.generate('hi',{}),{'reply':'hello'})

 def test_blank_key_on_same_endpoint_preserves_key(self):
  with tempfile.TemporaryDirectory() as t:
   m=ModelClient(t);m.save_settings({'base_url':'https://example.com/v1','model':'x','api_key':'s'})
   m.save_settings({'api_key':''});self.assertEqual(m.settings()['api_key'],'s')
 def test_legacy_local_provider_is_not_used(self):
  with tempfile.TemporaryDirectory() as t:
   m=ModelClient(t);m.config_path.write_text(json.dumps({'provider':'codex','model':'old','cli_path':'private-path'}),encoding='utf-8')
   self.assertEqual(m.settings()['provider'],'api');self.assertEqual(m.settings()['model'],'');self.assertFalse(hasattr(m,'_codex'))
 def test_key_control_characters_rejected_without_echo(self):
  with tempfile.TemporaryDirectory() as t:
   m=ModelClient(t)
   with self.assertRaises(ValueError) as caught:m.save_settings({'base_url':'http://127.0.0.1:9999/v1','model':'x','api_key':'FIRST_SECRET\nSECOND_SECRET'})
   self.assertNotIn('SECRET',str(caught.exception))
 def test_same_canonical_endpoint_keeps_key(self):
  with tempfile.TemporaryDirectory() as t:
   m=ModelClient(t);m.save_settings({'base_url':'https://example.com/v1','model':'x','api_key':'s'})
   m.save_settings({'base_url':'https://example.com/v1/','api_key':''});self.assertEqual(m.settings()['api_key'],'s')
