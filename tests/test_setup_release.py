import unittest,tempfile,threading,json,urllib.request,urllib.error,base64
from pathlib import Path
from server import make_server
class Model:
 def __init__(self):self.ready=False
 def public_settings(self):return dict(provider='api',ready=self.ready,model='fixture',effective_model='fixture',busy=False,has_api_key=False,base_url='http://127.0.0.1')
class SetupHTTPTests(unittest.TestCase):
 def test_goal_only_completion_requires_verified_model_and_real_selected_resource(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);model=Model();s=make_server(root,[],0,model);th=threading.Thread(target=s.serve_forever,daemon=True);th.start();url='http://127.0.0.1:'+str(s.server_port)
   def post(route,body):
    req=urllib.request.Request(url+route,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req) as r:return json.load(r)
   try:
    payload={'profile':{'goal':'学习摄影构图','topics':[]}}
    with self.assertRaises(urllib.error.HTTPError):post('/api/setup/complete',payload)
    model.ready=True
    with self.assertRaises(urllib.error.HTTPError):post('/api/setup/complete',payload)
    data=post('/api/resources/import-files',{'files':[{'name':'构图.md','data':base64.b64encode('# 构图\n三分法是一种构图方法。'.encode()).decode()}],'topic':'摄影'})
    payload['profile']['resource_ids']=[data['articles'][0]['id']]
    result=post('/api/setup/complete',payload);self.assertTrue(result['ready']);self.assertEqual(result['profile']['topics'],[])
   finally:s.shutdown();s.server_close();th.join()
