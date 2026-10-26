"""Optional, bounded GitHub stable release discovery; never executes downloaded code."""
from datetime import datetime,timezone
import json,re,ssl,threading,time,urllib.request,urllib.error
from app_info import REPOSITORY
try:import certifi
except ImportError:certifi=None

def version_tuple(value):
 if not isinstance(value,str) or not re.fullmatch(r'v?\d{1,5}\.\d{1,5}\.\d{1,5}',value):return None
 return tuple(int(x) for x in value.removeprefix('v').split('.'))

def choose_update(data,current,system,arch):
 empty=dict(available=False,status='current',current_version=current)
 if not isinstance(data,dict) or data.get('draft') is not False or data.get('prerelease') is not False:return empty
 tag=data.get('tag_name');new=version_tuple(tag);old=version_tuple(current)
 if not new or not old or new<=old:return empty
 version=tag.removeprefix('v')
 if system=='macos':names=[f'DailyStudy-{version}-macos-{arch}.dmg',f'DailyStudy-{version}-macos-{arch}.zip']
 elif system=='windows' and arch=='x64':names=[f'DailyStudy-{version}-windows-x64-setup.exe',f'DailyStudy-{version}-windows-x64.zip']
 else:return empty
 assets=data.get('assets',[])
 if not isinstance(assets,list):return empty
 for name in names:
  expected=f'https://github.com/{REPOSITORY}/releases/download/{tag}/{name}'
  for a in assets:
   if isinstance(a,dict) and a.get('name')==name and a.get('browser_download_url')==expected:
    return dict(available=True,status='available',current_version=current,version=version,download_url=expected,release_url=f'https://github.com/{REPOSITORY}/releases/tag/{tag}',notes=str(data.get('body') or '')[:12000],asset=name)
 return empty

def fetch_latest():
 context=ssl.create_default_context(cafile=certifi.where() if certifi else None)
 req=urllib.request.Request(f'https://api.github.com/repos/{REPOSITORY}/releases/latest',headers={'Accept':'application/vnd.github+json','User-Agent':'DailyStudy-update-check','X-GitHub-Api-Version':'2022-11-28'})
 try:
  with urllib.request.urlopen(req,timeout=12,context=context) as r:
   raw=r.read(2000001)
   if len(raw)>2000000:raise ValueError('Release response too large')
   return json.loads(raw)
 except urllib.error.HTTPError as e:
  if e.code==404:return {}
  raise

class UpdateChecker:
 def __init__(self,current,channel,system,arch,fetch=fetch_latest):
  self.current=current;self.channel=channel;self.system=system;self.arch=arch;self.fetch=fetch;self.lock=threading.Lock();self.last=0;self.result=None
 def check(self,force=False):
  if self.channel!='stable':return dict(available=False,status='preview',current_version=self.current)
  with self.lock:
   now=time.monotonic()
   if self.result is not None and now-self.last<(30 if force else 6*3600):return dict(self.result)
   try:self.result=choose_update(self.fetch(),self.current,self.system,self.arch)
   except (OSError,ValueError,TypeError,KeyError):
    self.result=dict(self.result or {},status='offline',current_version=self.current)
    self.result.setdefault('available',False)
   self.last=now;self.result['checked_at']=datetime.now(timezone.utc).isoformat()
   return dict(self.result)
