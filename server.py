from contextlib import closing
from datetime import datetime
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import argparse
import sys
import sqlite3
import zipfile
import tempfile
import os
import json
import mimetypes
from pathlib import Path
import threading
import time
from urllib.parse import parse_qs,urlsplit,unquote
from zoneinfo import ZoneInfo
from store import Store,today,valid_day
from model import ModelClient
from learning import Learning
from profile_settings import Profile
from resources import ResourceLibrary
from jobs import Jobs
from app_info import VERSION,public_info
from updates import UpdateChecker

STATIC=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'static'


def make_server(root,catalog,port=8765,model=None,channel='stable'):
    root=Path(root).resolve();store=Store(root,catalog);client=model or ModelClient(root);learning=Learning(store,client);profile=Profile(root);resources=ResourceLibrary(root,catalog,store,client);jobs=Jobs()

    info=public_info(channel);updater=UpdateChecker(VERSION,channel,info["platform"],info["arch"])

    def eligible(p):
        return [a for a in catalog if a.get('learning_unit',True) and not a.get('is_demo') and (p['use_existing'] or a['id'] in p['resource_ids'])]

    def setup_payload():
        p=profile.get();m=client.public_settings();marker=root/'学习台/data/migration.json'
        return dict(profile=p,model=m,library=dict(count=sum(a.get('learning_unit',True) and not a.get('is_demo') for a in catalog),topics=list(dict.fromkeys(a['topic'] for a in catalog if not a.get('is_demo'))),imported_legacy=marker.exists()),ready=p['onboarding_completed'] and m.get('ready',False),demo_id='welcome-demo',version=VERSION)

    def backup_data():
        folder=root/'备份';folder.mkdir(exist_ok=True);dest=folder/(datetime.now().strftime('%Y%m%d-%H%M%S')+'-日常学习.zip')
        with tempfile.TemporaryDirectory() as t:
            db=Path(t)/'study.sqlite3'
            with closing(sqlite3.connect(store.db)) as src,closing(sqlite3.connect(db)) as out,out:src.backup(out)
            with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
                for f in root.rglob('*'):
                    if not f.is_file() or f.is_symlink() or f.is_relative_to(folder) or f.is_relative_to(root/'WebView2') or f.name in ['study.sqlite3','study.sqlite3-wal','study.sqlite3-shm','模型设置.json','server.log','native-backend.log','.runtime.lock','.server-info.json','.window-state.json']:continue
                    z.write(f,str(f.relative_to(root)))
                z.write(db,'学习台/data/study.sqlite3')
        return dict(path=str(dest))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,format,*args):pass
        def send_json(self,value,status=200):
            data=json.dumps(value,ensure_ascii=False).encode();self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
        def host_ok(self):
            return self.headers.get('Host') in [f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}']
        def do_GET(self):
            if not self.host_ok():self.send_json({'error':'不允许的访问主机'},403);return
            u=urlsplit(self.path);q=parse_qs(u.query)
            day=q.get('date',[today()])[0]
            try:
                if u.path=='/api/app':return self.send_json(public_info(channel))
                if u.path=='/api/updates':return self.send_json(updater.check())
                if u.path=='/api/setup':return self.send_json(setup_payload())
                if u.path=='/api/browser-state':
                    f=store.data/'browser-transfer.json';return self.send_json(json.loads(f.read_text(encoding='utf-8')) if channel=='stable' and f.exists() else {})
                if u.path=='/api/demo':return self.send_json({'article_id':'welcome-demo'})
                if u.path=='/api/jobs':return self.send_json(jobs.get(q.get('id',[''])[0]))
                if u.path=='/api/status':
                    return self.send_json(dict(app='daily-study-local',today=today(),articles=len(catalog),topics=list(dict.fromkeys(a['topic'] for a in catalog)),model=client.public_settings(),read_ids=store.read_ids()))
                if u.path=='/api/catalog':return self.send_json(catalog)
                if u.path in ['/api/day','/api/plan']:return self.send_json(store._load(valid_day(day)))
                if u.path=='/api/history':return self.send_json(store.history())
                if u.path=='/api/handoff':return self.send_json(store.handoff(day))
                if u.path=='/api/review':return self.send_json(learning.public_review(day))
                if u.path=='/api/chats':return self.send_json(store.chats(q.get('date',[None])[0],q.get('article_id',[None])[0],q.get('session_id',[None])[0]))
                if u.path=='/api/chat/sessions':return self.send_json(store.chat_sessions(q.get('article_id',[''])[0]))
                if u.path=='/api/notes':return self.send_json(store.annotations(q.get('article_id',[None])[0]))
                if u.path=='/api/visits':return self.send_json(store.visits(day))
                if u.path=='/api/settings':return self.send_json(client.public_settings())
                if u.path=='/api/coverage':
                    f=store.data/'完整资料核对.json';return self.send_json(json.loads(f.read_text(encoding='utf-8')) if f.exists() else {})
                if u.path=='/api/article':
                    aid=q.get('id',[''])[0];a=store.catalog.get(aid)
                    if not a:return self.send_json({'error':'文章不存在'},404)
                    content=learning.text(aid)
                    if not a.get('is_demo'):store.visit(aid)
                    try:session=store.chat_session(aid,q.get('session_id',[None])[0])
                    except ValueError:session=store.chat_session(aid)
                    return self.send_json(dict(article=a,content=content,annotations=store.annotations(aid),session_id=session['id'],sessions=store.chat_sessions(aid),chats=store.chats(article_id=aid,session_id=session['id'])))
                if u.path.startswith('/api/'):return self.send_json({'error':'接口不存在'},404)
                rel=unquote(u.path).lstrip('/') or 'index.html';p=(STATIC/rel).resolve()
                if not p.is_relative_to(STATIC) or not p.is_file():return self.send_json({'error':'页面不存在'},404)
                data=p.read_bytes();self.send_response(200)
                self.send_header('Content-Type',mimetypes.guess_type(p)[0] or 'application/octet-stream');self.send_header('Content-Length',str(len(data)))
                self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-cache');self.send_header('Referrer-Policy','no-referrer')
                self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' https: data:; connect-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
                self.end_headers();self.wfile.write(data)
            except (ValueError,KeyError) as e:self.send_json({'error':str(e)},400)
            except (BrokenPipeError,ConnectionResetError):pass
            except Exception:self.send_json({'error':'读取失败，请检查本地服务状态'},500)

        def do_POST(self):
            if not self.host_ok():return self.send_json({'error':'不允许的访问主机'},403)
            origin=self.headers.get('Origin');expected={f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}
            if (origin and origin not in expected) or self.headers.get('Sec-Fetch-Site')=='cross-site':return self.send_json({'error':'拒绝跨站修改'},403)
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send_json({'error':'需要JSON请求'},415)
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=48*1024*1024:return self.send_json({'error':'请求体大小无效'},400)
                p=json.loads(self.rfile.read(n))
                if not isinstance(p,dict):raise ValueError('请求必须是对象')
                route=urlsplit(self.path).path
                if route=='/api/updates/check':return self.send_json(updater.check(force=True))
                if route=='/api/browser-state/complete':
                    f=store.data/'browser-transfer.json'
                    if channel=='stable' and f.exists() and json.loads(f.read_text(encoding='utf-8')).get('id')==p.get('id'):f.rename(f.with_suffix('.imported'))
                    return self.send_json({'ok':True})
                if route=='/api/setup/draft':return self.send_json(profile.save(p.get('profile',{})))
                if route=='/api/setup/complete':
                    value=profile.save(p.get('profile',{}))
                    if not client.public_settings().get('ready'):raise ValueError('请先验证模型连接')
                    if not value['goal']:raise ValueError('请填写学习目标')
                    if not eligible(value):raise ValueError('请先选择或导入至少一份真实学习资料')
                    profile.save({},completed=True);return self.send_json(setup_payload())
                if route=='/api/model/test':return self.send_json(client.test_connection())
                if route=='/api/resources/delete':
                    with learning.lock:
                        return self.send_json(resources.delete(p.get('article_ids')))
                if route=='/api/resources/import-files':return self.send_json({'articles':resources.import_files(p.get('files'),p.get('topic','我的资料'))})
                if route=='/api/resources/preview':return self.send_json(resources.preview_url(p.get('url','')))
                if route=='/api/resources/import-url':return self.send_json({'articles':[resources.import_url(p.get('url',''),p.get('topic','网络资料'))]})
                if route=='/api/resources/discover':
                    if not client.public_settings().get('ready'):raise ValueError('请先验证模型连接')
                    prefs=profile.get();given=p.get('preferences',{});prefs.update({k:given[k] for k in ['goal','topics','level','pace'] if k in given})
                    return self.send_json(jobs.submit(lambda:resources.discover(prefs,p.get('query',''),scope=p.get('scope','onboarding'))))
                if route=='/api/jobs/cancel':return self.send_json(jobs.cancel(p.get('id','')))
                if route=='/api/tour':return self.send_json(profile.save({'tour_step':p.get('step',0),'tour_completed':bool(p.get('completed',False))}))
                if route=='/api/data/backup':return self.send_json(backup_data())
                if route=='/api/check':
                    with learning.lock:return self.send_json(store.toggle(p['date'],p['article_id'],p['done']))
                if route=='/api/plan/edit':
                    with learning.lock:return self.send_json(store.edit_day(p['date'],p))
                if route=='/api/plan/add':
                    with learning.lock:return self.send_json(store.add_article(p['date'],p['article_id']))
                if route=='/api/ai/plan':return self.send_json(learning.plan(p.get('date',today())))
                if route=='/api/ai/context':return self.send_json(learning.prepare_context(p['article_id'],p.get('quote',''),p.get('section_index'),p.get('session_id'),p.get('include_images',True)))
                if route=='/api/ai/ask':return self.send_json(learning.ask(p['article_id'],p['question'],p.get('quote',''),p.get('section_index'),p.get('session_id'),p.get('images'),p.get('text_only',False)))
                if route=='/api/chat/new':
                    session=store.new_chat_session(p['article_id']);return self.send_json(dict(session_id=session['id'],sessions=store.chat_sessions(p['article_id']),chats=[]))
                if route=='/api/note':return self.send_json(learning.annotate(p['article_id'],p['quote'],p['kind'],p.get('note',''),p.get('prefix',''),p.get('suffix','')))
                if route=='/api/note/delete':store.delete_annotation(p['id']);return self.send_json({'ok':True})
                if route=='/api/ai/review':return self.send_json(learning.start_review(p.get('date',today()),additional=p.get('additional',False)))
                if route=='/api/ai/grade':return self.send_json(learning.answer_review(p['date'],p['question_id'],p['answer']))
                if route=='/api/settings':return self.send_json(client.save_settings(p))
                return self.send_json({'error':'接口不存在'},404)
            except (ValueError,KeyError,TypeError) as e:self.send_json({'error':str(e)},400)
            except (BrokenPipeError,ConnectionResetError):pass
            except RuntimeError as e:self.send_json({'error':str(e)},502)
            except Exception:self.send_json({'error':'本次操作未完成；已保存的学习记录保留，请重试或检查本地服务'},500)

    httpd=ThreadingHTTPServer(('127.0.0.1',port),Handler);httpd.daemon_threads=True
    httpd.store=store;httpd.model=client;httpd.learning=learning;httpd.profile=profile;httpd.resources=resources;httpd.jobs=jobs
    return httpd


def start_scheduler(server):
    def work():
        path=server.store.data/'自动任务记录.json'
        while True:
            try:
                cfg=server.profile.get()
                if not cfg.get('onboarding_completed') or not server.model.public_settings().get('ready'):
                    time.sleep(30);continue
                now=datetime.now(ZoneInfo('Asia/Shanghai'));day=now.date().isoformat();clock=now.strftime('%H:%M')
                runs=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
                for kind,flag,when in [('plan','auto_plan','plan_time'),('review','auto_review','review_time')]:
                    key=day+':'+kind
                    if not cfg.get(flag) or clock<cfg[when] or key in runs:continue
                    if kind=='review' and not server.store.handoff(day)['completed']:continue
                    runs[key]={'status':'running','started':now.isoformat()};path.write_text(json.dumps(runs,ensure_ascii=False,indent=2),encoding='utf-8')
                    try:
                        if kind=='plan':server.learning.plan(day)
                        else:server.learning.start_review(day)
                        runs[key]['status']='completed'
                    except Exception as e:runs[key]={'status':'failed','message':str(e)[:300],'retry':'需手动重试，不自动反复调用模型'}
                    path.write_text(json.dumps(runs,ensure_ascii=False,indent=2),encoding='utf-8')
            except Exception:pass
            time.sleep(30)
    t=threading.Thread(target=work,daemon=True,name='study-scheduler');t.start()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',default=str(Path(__file__).resolve().parent.parent));parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    root=Path(args.root);catalog=json.loads((root/'学习台/data/catalog.json').read_text(encoding='utf-8'))
    server=make_server(root,catalog,args.port);start_scheduler(server)
    print(f'日常学习台：http://127.0.0.1:{server.server_port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
