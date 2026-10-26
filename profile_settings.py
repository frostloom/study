"""Persistent onboarding/preferences independent of learning facts."""
from pathlib import Path
import copy,json,re,threading
DEFAULTS=dict(version=1,onboarding_completed=False,wizard_step=0,name='',goal='',topics=[],level='intermediate',pace='balanced',daily_minutes=90,review_minutes=30,auto_plan=False,auto_review=False,plan_time='08:00',review_time='21:00',resource_ids=[],use_existing=False,known_progress='',tour_completed=False,tour_step=0)
class Profile:
 def __init__(self,root):self.root=Path(root);self.path=self.root/'学习台/data/profile.json';self.lock=threading.RLock()
 def get(self):
  d=copy.deepcopy(DEFAULTS)
  if self.path.exists():d.update(json.loads(self.path.read_text(encoding='utf-8')))
  return d
 def budget(self):
  d=self.get();return d['daily_minutes']-d['review_minutes'],d['review_minutes']
 def save(self,patch,completed=None):
  if not isinstance(patch,dict):raise ValueError('设置必须是对象')
  with self.lock:
   d=self.get()
   for k,v in patch.items():
    if k not in DEFAULTS or k in ['version','onboarding_completed']:continue
    if k in ['topics','resource_ids']:
     if not isinstance(v,list) or len(v)>10000 or any(not isinstance(x,str) or len(x)>150 for x in v):raise ValueError('资料或主题列表无效')
     d[k]=list(dict.fromkeys(x.strip() for x in v if x.strip()))
    elif k in ['auto_plan','auto_review','use_existing','tour_completed']:
     if type(v) is not bool:raise ValueError('开关值无效')
     d[k]=v
    elif k in ['daily_minutes','review_minutes','wizard_step','tour_step']:
     if type(v) is not int:raise ValueError('时间和步骤必须为整数')
     d[k]=v
    else:
     if not isinstance(v,str) or len(v)>2000:raise ValueError('设置文字过长或格式无效')
     d[k]=v.strip()
   if not 15<=d['daily_minutes']<=480 or not 5<=d['review_minutes']<=d['daily_minutes']-5:raise ValueError('每天总时长需15–480分钟，复习至少5分钟且少于总时长')
   if not 0<=d['wizard_step']<=5 or not 0<=d['tour_step']<=10:raise ValueError('步骤无效')
   if d['pace'] not in ['quick','foundations','balanced'] or d['level'] not in ['beginner','intermediate','advanced']:raise ValueError('学习方式或基础程度无效')
   for k in ['plan_time','review_time']:
    if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',d[k]):raise ValueError('时间格式应为HH:MM')
   if completed is not None:d['onboarding_completed']=bool(completed)
   self.path.parent.mkdir(parents=True,exist_ok=True);tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(self.path)
   return d
