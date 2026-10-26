"""Local study state. SQLite is authoritative; JSON is an assistant handoff."""
from contextlib import contextmanager
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re
import sqlite3
import threading
import uuid
from zoneinfo import ZoneInfo


def valid_day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('日期必须为 YYYY-MM-DD')
    return date.fromisoformat(value).isoformat()


def today():
    return datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()


class Store:
    def __init__(self, root, catalog):
        self.root = Path(root).resolve()
        self.data = self.root/'学习台/data'
        self.data.mkdir(parents=True, exist_ok=True)
        self.db = self.data/'study.sqlite3'
        self.catalog = {a['id']: a for a in catalog}
        self.lock = threading.RLock()
        with self.connect() as c:
            c.executescript('''
              CREATE TABLE IF NOT EXISTS deleted_resources(article_id TEXT PRIMARY KEY, body TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS plans(day TEXT PRIMARY KEY, body TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS checks(day TEXT, article_id TEXT, done INTEGER NOT NULL,
                updated TEXT NOT NULL, PRIMARY KEY(day,article_id));
              CREATE TABLE IF NOT EXISTS annotations(id TEXT PRIMARY KEY, article_id TEXT NOT NULL,
                body TEXT NOT NULL, created TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS conversations(id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT NOT NULL, article_id TEXT, body TEXT NOT NULL, created TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS chat_sessions(id TEXT PRIMARY KEY, article_id TEXT NOT NULL, created TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS reviews(day TEXT PRIMARY KEY, body TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS prior_readings(article_id TEXT PRIMARY KEY, confirmed_at TEXT NOT NULL, note TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS visits(day TEXT, article_id TEXT, count INTEGER NOT NULL,
                last_seen TEXT NOT NULL, PRIMARY KEY(day,article_id));
            ''')
            # Preserve every legacy message, assigning one original session per article.
            rows=c.execute('SELECT id,article_id,body,created FROM conversations ORDER BY id').fetchall()
            for row in rows:
                body=json.loads(row['body']);sid=body.get('session_id') or uuid.uuid5(uuid.NAMESPACE_URL,'study-legacy:'+str(row['article_id'])).hex
                c.execute('INSERT OR IGNORE INTO chat_sessions VALUES (?,?,?)',(sid,row['article_id'],row['created']))
                if not body.get('session_id'):
                    body['session_id']=sid;c.execute('UPDATE conversations SET body=? WHERE id=?',(json.dumps(body,ensure_ascii=False),row['id']))

        with self.connect() as c:
            self.deleted={r['article_id']:json.loads(r['body']) for r in c.execute('SELECT * FROM deleted_resources')}
        self.catalog={aid:a for aid,a in self.catalog.items() if aid not in self.deleted}

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.db, timeout=30)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    def _load(self, day):
        valid_day(day)
        with self.connect() as c:
            row = c.execute('SELECT body FROM plans WHERE day=?', (day,)).fetchone()
            checks = {r['article_id']: bool(r['done']) for r in c.execute(
                'SELECT article_id,done FROM checks WHERE day=?', (day,))}
        if not row: return None
        p = json.loads(row['body'])
        p['items']=[x for x in p['items'] if x['article_id'] in self.catalog or (checks.get(x['article_id']) and x['article_id'] in self.deleted)]
        for item in p['items']+p.get('removed_items',[]):
            article = self.catalog.get(item['article_id']) or self.deleted.get(item['article_id'])
            if not article:continue
            item['deleted']=item['article_id'] not in self.catalog
            item.update(title=article['title'], topic=article['topic'], source_url=article['source_url'],
                        done=checks.get(item['article_id'], False))
        p['completed_minutes'] = sum(x['minutes'] for x in p['items'] if x.get('done'))
        p['planned_minutes'] = sum(x['minutes'] for x in p['items'])
        return p

    def generate_plan(self, day, reading_minutes=120, review_minutes=60):
        reading,review=reading_minutes,review_minutes
        valid_day(day)
        if reading_minutes != 120 or review_minutes != 60:
            raise ValueError('当前每日约定为120分钟阅读+60分钟复习')
        with self.lock:
            old = self._load(day)
            if old: return old
            with self.connect() as c:
                read = {r['article_id'] for r in c.execute(
                    'SELECT article_id FROM checks WHERE done=1 AND day<?', (day,))}
                prior = list(c.execute('SELECT day,body FROM plans WHERE day<? ORDER BY day DESC', (day,)))
            items=[]; selected=set(); carry_budget=60
            # Only the latest three planned days can supply backlog; don't stack an endless debt.
            for row in prior[:3]:
                p = self._load(row['day'])
                for item in p['items']:
                    aid=item['article_id']; a=self.catalog.get(aid)
                    if not a or aid in read or aid in selected or item.get('done'): continue
                    cost=a['minutes']
                    if cost > carry_budget: continue
                    items.append(dict(article_id=aid, minutes=cost, kind='carry', origin_day=row['day']))
                    selected.add(aid); carry_budget-=cost
            remaining=reading_minutes-sum(x['minutes'] for x in items)
            # A rotating main topic keeps a day coherent, but never requires completing a whole
            # large column before any other topic appears. Morning assistant can replace the plan.
            available=[a for a in self.catalog.values() if a['id'] not in read|selected and not a.get('optional')]
            topic_order=list(dict.fromkeys(a['topic'] for a in available))
            if topic_order:
                focus=topic_order[len(prior)%len(topic_order)]
                available.sort(key=lambda a:(a['topic']!=focus, topic_order.index(a['topic'])))
            else: focus='复习与补充'
            for a in available:
                cost=a['minutes']
                if cost>remaining: continue
                items.append(dict(article_id=a['id'],minutes=cost,kind='new',origin_day=None))
                selected.add(a['id']); remaining-=cost
                if remaining<8: break
            p=dict(id=f'day-{day}',revision=uuid.uuid4().hex,date=day,reading_minutes=reading,review_minutes=review,
                   focus=focus,note='基础计划：完整文章阅读；早晨助手可根据昨晚复盘调整。阅读估时不是硬性截止时间。',items=items)
            with self.connect() as c:
                c.execute('INSERT OR IGNORE INTO plans(day,body) VALUES (?,?)',(day,json.dumps(p,ensure_ascii=False)))
            self.export(day)
            return self._load(day)

    def toggle(self, day, article_id, done):
        valid_day(day)
        if not isinstance(done, bool): raise ValueError('勾选状态必须为布尔值')
        with self.lock:
            p=self._load(day)
            if not p or article_id not in self.catalog or article_id not in {x['article_id'] for x in p['items']}:
                raise ValueError('文章不在这一天的待办中')
            with self.connect() as c:
                c.execute('INSERT INTO checks VALUES (?,?,?,?) ON CONFLICT(day,article_id) DO UPDATE SET done=excluded.done,updated=excluded.updated',
                          (day,article_id,int(done),datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()))
            self.reconcile_review(day)
            self.export(day)
            return self._load(day)

    def budget(self):
        if not (self.data/'profile.json').exists():return 120,60
        from profile_settings import Profile
        return Profile(self.root).budget()

    def replace_plan(self, day, article_ids, note='由学习助手按实际复盘安排',allocations=None,scopes=None):
        valid_day(day)
        if not isinstance(article_ids,list) or len(article_ids)!=len(set(article_ids)):
            raise ValueError('文章ID必须为无重复列表')
        if any(a not in self.catalog for a in article_ids): raise ValueError('资料ID不存在')
        with self.lock:
            if any(a not in self.catalog for a in article_ids):raise ValueError('资料已删除，请重新生成计划')
            old=self._load(day)
            done={x['article_id'] for x in old['items'] if x.get('done') and not x.get('deleted')} if old else set()
            if not done.issubset(article_ids): raise ValueError('不能移除当天已完成的项目')
            reading,review=self.budget()
            if old:reading,review=old.get('reading_minutes',reading),old.get('review_minutes',review)
            allocations=allocations or {};scopes=scopes or {}
            minutes={a:allocations.get(a,self.catalog[a]['minutes']) for a in article_ids}
            if any(type(v) is not int or not 1<=v<=self.catalog[a]['minutes'] for a,v in minutes.items()):raise ValueError('阅读安排时间无效')
            archived=[x for x in old['items'] if x.get('deleted') and x.get('done')] if old else []
            cost=sum(minutes.values())+sum(x['minutes'] for x in archived)
            if cost>reading:raise ValueError(f'阅读估时超过当天的{reading}分钟预算，请减少内容')
            p=dict(id=f'day-{day}',revision=uuid.uuid4().hex,date=day,reading_minutes=reading,review_minutes=review,
                   focus=self.catalog[article_ids[0]]['topic'] if article_ids else '复习与补充',
                   note=str(note)[:1000],items=[dict(article_id=a,minutes=minutes[a],scope=str(scopes.get(a,''))[:1000],partial=minutes[a]<self.catalog[a]['minutes'],kind='new',origin_day=None) for a in article_ids]+archived)
            if old and old.get('removed_items'):p['removed_items']=old['removed_items']
            with self.connect() as c:c.execute('INSERT INTO plans VALUES (?,?) ON CONFLICT(day) DO UPDATE SET body=excluded.body',(day,json.dumps(p,ensure_ascii=False)))
            self.export(day)
            return self._load(day)

    def reconcile_review(self,day):
        r=self.review(day)
        if not r:return
        allowed={x['id'] for x in self.handoff(day)['completed']}
        questions=[q for q in r['questions'] if q.get('answer') or q.get('grade') or set(q.get('article_ids',[])).issubset(allowed)]
        r['questions']=questions
        invalidated=set(r.get('invalidated_article_ids',[])) | (set(r.get('completed_article_ids',[]))-allowed)
        r['invalidated_article_ids']=sorted(invalidated)
        r['completed_article_ids']=sorted(({a for q in questions for a in q.get('article_ids',[])} & allowed)-invalidated)
        r['status']='已完成' if questions and all(q.get('grade') for q in questions) else '进行中' if questions else '待作答'
        self.save_review(day,r)

    def edit_day(self,day,patch):
        """Manual tasks affect this day only; removed snapshots retain learning facts."""
        valid_day(day)
        if not isinstance(patch,dict):raise ValueError('任务设置格式无效')
        with self.lock:
            p=self._load(day)
            if not p:
                reading,review=self.budget()
                p=dict(id='day-'+day,date=day,reading_minutes=reading,review_minutes=review,focus='自主安排',note='按当天时间自主安排',items=[])
            if 'expected_revision' in patch and patch['expected_revision']!=p.get('revision',''):raise ValueError('当天计划已有更新，请关闭窗口并重新打开后修改')
            action=patch.get('action');aid=patch.get('article_id');items=p['items'];removed=p.setdefault('removed_items',[])
            if action in ['add','update']:
                a=self.catalog.get(aid)
                if not a or a.get('is_demo') or not a.get('learning_unit',True):raise ValueError('请选择资料库中的完整章节')
                item=next((x for x in items if x['article_id']==aid),None)
                if action=='add' and item:return p
                if action=='update' and not item:raise ValueError('任务不存在')
                if action=='update' and item.get('done'):raise ValueError('修改已完成任务的范围前，请先取消完成勾选')
                minutes=patch.get('minutes',min(a['minutes'],30));scope=patch.get('scope','')
                if type(minutes) is not int or not 1<=minutes<=a['minutes']:raise ValueError('阅读分钟数应为1至章节估时之间的整数')
                if not isinstance(scope,str) or len(scope)>1000:raise ValueError('阅读范围最多1000字')
                if not item:
                    archived=next((x for x in removed if x['article_id']==aid and x.get('done')),None)
                    if archived and (minutes!=archived['minutes'] or scope.strip()!=archived.get('scope','')):raise ValueError('该章节已有当天完成记录，请先按原范围恢复，再取消完成后修改')
                    item=dict(archived) if archived else dict(article_id=aid,kind='manual',origin_day=None);items.append(item)
                item.update(minutes=minutes,scope=scope.strip(),partial=minutes<a['minutes'])
                p['removed_items']=[x for x in removed if x['article_id']!=aid]
                p['reading_minutes']=max(p['reading_minutes'],sum(x['minutes'] for x in items))
            elif action=='remove':
                item=next((x for x in items if x['article_id']==aid),None)
                if not item:raise ValueError('任务不存在')
                p['removed_items']=[x for x in removed if x['article_id']!=aid]+[{**item,'removed_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()}]
                p['items']=[x for x in items if x['article_id']!=aid]
            elif action=='save':
                tasks=patch.get('tasks')
                if not isinstance(tasks,list) or len(tasks)>480:raise ValueError('任务列表无效')
                ids=[];new=[]
                for task in tasks:
                    if not isinstance(task,dict):raise ValueError('任务格式无效')
                    tid=task.get('article_id');a=self.catalog.get(tid)
                    if tid in ids or not a or a.get('is_demo') or not a.get('learning_unit',True):raise ValueError('任务重复或资料不存在')
                    ids.append(tid);prior=next((x for x in items if x['article_id']==tid),None) or next((x for x in removed if x['article_id']==tid and x.get('done')),None)
                    minutes=task.get('minutes');scope=task.get('scope','')
                    if type(minutes) is not int or not 1<=minutes<=a['minutes'] or not isinstance(scope,str) or len(scope)>1000:raise ValueError('阅读分钟数或范围无效')
                    if prior and prior.get('done') and (minutes!=prior['minutes'] or scope.strip()!=prior.get('scope','')):raise ValueError('修改已完成任务的范围前，请先取消完成勾选')
                    new.append({**(prior or dict(article_id=tid,kind='manual',origin_day=None)),**dict(minutes=minutes,scope=scope.strip(),partial=minutes<a['minutes'])})
                p['removed_items']=[x for x in removed if x['article_id'] not in ids]+[{**x,'removed_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()} for x in items if x['article_id'] not in ids]
                p['items']=new
                for key in ['reading_minutes','review_minutes']:
                    if key in patch:
                        if type(patch[key]) is not int:raise ValueError('当天时长必须为整数')
                        p[key]=patch[key]
                if 'reading_minutes' not in patch:p['reading_minutes']=max(p['reading_minutes'],sum(x['minutes'] for x in new))
            elif action=='budget':
                for key in ['reading_minutes','review_minutes']:
                    if type(patch.get(key)) is not int:raise ValueError('当天时长必须为整数')
                    p[key]=patch[key]
            else:raise ValueError('未知的计划调整操作')
            if not 0<=p['reading_minutes'] or p['review_minutes']<5 or p['reading_minutes']+p['review_minutes']>480:raise ValueError('当天总时长不能超过480分钟，复习至少5分钟')
            if sum(x['minutes'] for x in p['items'])>p['reading_minutes']:raise ValueError('阅读预算小于待办估时，请先调整任务分钟数或移除部分章节')
            p['manually_adjusted']=True;p['revision']=uuid.uuid4().hex
            with self.connect() as c:c.execute('INSERT INTO plans VALUES (?,?) ON CONFLICT(day) DO UPDATE SET body=excluded.body',(day,json.dumps(p,ensure_ascii=False)))
            self.reconcile_review(day);self.export(day)
            return self._load(day)

    def add_article(self, day, aid):
        p=self._load(valid_day(day)) or {}
        archived=next((x for x in p.get('removed_items',[]) if x['article_id']==aid and x.get('done')),None)
        return self.edit_day(day,{'action':'add','article_id':aid,'minutes':archived['minutes'] if archived else self.catalog.get(aid,{}).get('minutes',30),'scope':archived.get('scope','') if archived else ''})

    def recent_plan_days(self,day):
        valid_day(day)
        with self.connect() as c:return [r['day'] for r in c.execute('SELECT day FROM plans WHERE day<? ORDER BY day DESC LIMIT 3',(day,))]

    def handoff(self, day):
        p=self._load(valid_day(day))
        if not p:return dict(date=day,completed=[],pending=[],assessment_status='尚未生成计划')
        def article(x):
            a=dict(self.catalog[x['article_id']]);a.update(done=x.get('done',False),partial=x.get('partial',False),scope=x.get('scope',''));return a
        return dict(date=day,completed=[article(x) for x in p['items'] if x.get('done') and not x.get('deleted')],
                    pending=[article(x) for x in p['items'] if not x.get('done') and not x.get('deleted')],
                    completed_minutes=p['completed_minutes'],review_minutes=p.get('review_minutes',60),
                    assessment_status='待网页AI复习',
                    instruction='仅对completed中的完整文章在网页逐题提问。勾选只代表已读，不代表掌握；未收到回答不要评分。')

    def history(self):
        with self.connect() as c:
            days=[r['day'] for r in c.execute('SELECT day FROM plans UNION SELECT day FROM conversations UNION SELECT day FROM reviews UNION SELECT day FROM visits ORDER BY day DESC')]
        result=[]
        for d in days:
            p=self._load(d);r=self.review(d)
            if p:
                p['items']=p['items']+[x for x in p.get('removed_items',[]) if x.get('done')]
                p['completed_minutes']=sum(x['minutes'] for x in p['items'] if x.get('done'))
                p['planned_minutes']=sum(x['minutes'] for x in p['items'])
            result.append(dict(date=d,total=len(p['items']) if p else 0,done=sum(x.get('done',False) for x in p['items']) if p else 0,
                completed_minutes=p['completed_minutes'] if p else 0,planned_minutes=p['planned_minutes'] if p else 0,
                review_total=len(r['questions']) if r else 0,review_answered=sum(bool(q.get('grade')) for q in r['questions']) if r else 0))
        return result

    def read_ids(self):
        with self.connect() as c:
            done=c.execute('SELECT checks.article_id,plans.body FROM checks LEFT JOIN plans ON checks.day=plans.day WHERE checks.done=1').fetchall()
            result={r['article_id'] for r in c.execute('SELECT article_id FROM prior_readings')}
        for row in done:
            body=json.loads(row['body']) if row['body'] else {}
            items=body.get('items',[])+body.get('removed_items',[])
            task=next((x for x in items if x['article_id']==row['article_id']),{})
            if not task.get('partial'):result.add(row['article_id'])
        return sorted(result)

    def export(self, day):
        h=self.handoff(day);folder=self.data/'复习交接';folder.mkdir(exist_ok=True)
        target=folder/f'{day}.json';tmp=target.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(h,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(target)
        plans=self.root/'每日计划';plans.mkdir(exist_ok=True)
        p=self._load(day)
        lines=[f'# {day} 学习台待办\n',f'阅读约{self._load(day)["reading_minutes"]}分钟，复习答题约{self._load(day)["review_minutes"]}分钟。勾选状态以SQLite为准。\n']
        for item in p['items']:
            a=self.catalog.get(item['article_id']) or self.deleted[item['article_id']]
            lines.append(f'- [{"x" if item.get("done") else " "}] {a["title"]}（{a["topic"]}，约{a["minutes"]}分钟，ID `{a["id"]}`）')
        dest=plans/f'{day}-学习台.md';tmp=dest.with_suffix('.md.tmp');tmp.write_text('\n'.join(lines)+'\n',encoding='utf-8');tmp.replace(dest)

    def annotations(self, article_id=None):
        with self.connect() as c:
            rows=c.execute('SELECT body FROM annotations'+(' WHERE article_id=?' if article_id else '')+' ORDER BY created DESC',
                           (article_id,) if article_id else ()).fetchall()
        return [json.loads(r['body']) for r in rows]

    def save_annotation(self, article_id, quote, kind, note='', prefix='', suffix=''):
        if article_id not in self.catalog:raise ValueError('文章不存在')
        if kind not in ['highlight','note']:raise ValueError('批注类型无效')
        if not isinstance(quote,str) or not quote.strip() or len(quote)>8000:raise ValueError('请选择1–8000字正文')
        if not isinstance(note,str) or len(note)>10000:raise ValueError('批注过长')
        n=dict(id=uuid.uuid4().hex,article_id=article_id,quote=quote,kind=kind,note=note,
               prefix=str(prefix)[-100:],suffix=str(suffix)[:100],created=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat())
        with self.lock,self.connect() as c:c.execute('INSERT INTO annotations VALUES (?,?,?,?)',(n['id'],article_id,json.dumps(n,ensure_ascii=False),n['created']))
        return n

    def delete_annotation(self, annotation_id):
        with self.lock,self.connect() as c:c.execute('DELETE FROM annotations WHERE id=?',(annotation_id,))

    def new_chat_session(self,article_id):
        if article_id not in self.catalog:raise ValueError('文章不存在')
        session=dict(id=uuid.uuid4().hex,article_id=article_id,created=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat())
        with self.lock,self.connect() as c:c.execute('INSERT INTO chat_sessions VALUES (?,?,?)',(session['id'],article_id,session['created']))
        return session

    def chat_session(self,article_id,session_id=None):
        if article_id not in self.catalog:raise ValueError('文章不存在')
        with self.lock:
            with self.connect() as c:
                if session_id is not None:
                    if not isinstance(session_id,str) or len(session_id)>80:raise ValueError('会话无效')
                    row=c.execute('SELECT * FROM chat_sessions WHERE id=? AND article_id=?',(session_id,article_id)).fetchone()
                    if row is None:raise ValueError('会话不存在或不属于当前文章')
                else:row=c.execute('SELECT * FROM chat_sessions WHERE article_id=? ORDER BY created DESC,id DESC LIMIT 1',(article_id,)).fetchone()
            return dict(row) if row else self.new_chat_session(article_id)

    def chat_sessions(self,article_id):
        if article_id not in self.catalog:raise ValueError('文章不存在')
        with self.connect() as c:rows=c.execute('SELECT * FROM chat_sessions WHERE article_id=? ORDER BY created DESC,id DESC',(article_id,)).fetchall()
        messages=self.chats(article_id=article_id);result=[]
        for row in rows:
            owned=[m for m in messages if m.get('session_id')==row['id']]
            result.append(dict(row)|dict(title=(owned[0]['question'][:45] if owned else '新对话'),count=len(owned),legacy=row['id']==uuid.uuid5(uuid.NAMESPACE_URL,'study-legacy:'+article_id).hex))
        return result

    def add_chat(self, article_id, question, reply, quote='', section_index=None, section_title='', session_id=None, context=None):
        d=today();now=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
        with self.lock:
            session=self.chat_session(article_id,session_id)
            body=dict(article_id=article_id,question=question,reply=reply,quote=quote,section_index=section_index,section_title=section_title,session_id=session['id'],created=now,date=d)
            if context is not None:body['context']=context
            with self.connect() as c:c.execute('INSERT INTO conversations(day,article_id,body,created) VALUES (?,?,?,?)',(d,article_id,json.dumps(body,ensure_ascii=False),now))
        return body

    def chats(self, day=None, article_id=None, session_id=None):
        conditions=[];params=[]
        if day:conditions.append('day=?');params.append(valid_day(day))
        if article_id:conditions.append('article_id=?');params.append(article_id)
        if session_id is not None and article_id:self.chat_session(article_id,session_id)
        with self.connect() as c:
            rows=c.execute('SELECT body FROM conversations'+(' WHERE '+' AND '.join(conditions) if conditions else '')+' ORDER BY id',params).fetchall()
        items=[json.loads(r['body']) for r in rows]
        return [m for m in items if m.get('session_id')==session_id] if session_id is not None else items

    def visit(self,article_id):
        if article_id not in self.catalog:raise ValueError('文章不存在')
        now=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
        with self.lock,self.connect() as c:c.execute('INSERT INTO visits VALUES (?,?,1,?) ON CONFLICT(day,article_id) DO UPDATE SET count=count+1,last_seen=excluded.last_seen',(today(),article_id,now))

    def visits(self,day):
        with self.connect() as c:return [dict(r) for r in c.execute('SELECT * FROM visits WHERE day=? ORDER BY last_seen DESC',(valid_day(day),))]

    def review(self,day):
        with self.connect() as c:r=c.execute('SELECT body FROM reviews WHERE day=?',(valid_day(day),)).fetchone()
        return json.loads(r['body']) if r else None

    def save_review(self,day,review):
        valid_day(day)
        with self.lock,self.connect() as c:c.execute('INSERT INTO reviews VALUES (?,?) ON CONFLICT(day) DO UPDATE SET body=excluded.body',(day,json.dumps(review,ensure_ascii=False)))
        folder=self.root/'晚间复盘';folder.mkdir(exist_ok=True)
        dest=folder/f'{day}-网页复习.json';tmp=dest.with_suffix('.json.tmp');tmp.write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(dest)
