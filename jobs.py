"""Bounded background discovery; only confirmed imports change the library."""
import threading,uuid,time,copy
class Jobs:
 def __init__(self):self.items={};self.lock=threading.RLock()
 def submit(self,fn):
  with self.lock:
   if sum(x['state'] in ['queued','running'] for x in self.items.values())>=2:raise ValueError('已有资料查找正在进行，请稍候或取消后再试')
   job=dict(id=uuid.uuid4().hex,state='queued',phase='等待模型与网络',created=time.time());self.items[job['id']]=job
  def run():
   with self.lock:
    if job['state']=='cancelled':return
    job.update(state='running',phase='根据偏好生成关键词、检索公开资料并排序')
   try:
    result=fn()
    with self.lock:
     if job['state']!='cancelled':job.update(state='completed',phase='已找到资料',result=result)
   except Exception as e:
    with self.lock:
     if job['state']!='cancelled':job.update(state='failed',phase='查找未完成',error=str(e)[:500])
  threading.Thread(target=run,daemon=True,name='resource-discovery').start();return {'job_id':job['id']}
 def get(self,key):
  with self.lock:
   if key not in self.items:raise ValueError('任务不存在')
   return copy.deepcopy(self.items[key])
 def cancel(self,key):
  with self.lock:
   if key not in self.items:raise ValueError('任务不存在')
   if self.items[key]['state'] in ['running','queued']:self.items[key].update(state='cancelled',phase='已取消；当前网络请求将安全结束')
   return copy.deepcopy(self.items[key])
