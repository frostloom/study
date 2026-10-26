import tempfile
import unittest
from pathlib import Path
from store import Store
try:
    from learning import Learning
except ImportError:Learning=None

class FakeModel:
    """Controlled model boundary, not the behavior under test."""
    def __init__(self,outputs):self.outputs=list(outputs)
    def generate(self,prompt,schema=None):return self.outputs.pop(0)

class LearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        (self.root/'资料源').mkdir();(self.root/'资料源/a.md').write_text('# 正文\n实际事务原理与完整末尾',encoding='utf-8')
        self.catalog=[dict(id='a',title='事务',topic='MySQL',minutes=30,path='资料源/a.md',source_url='https://example.com/a')]
        self.store=Store(self.root,self.catalog)
    def tearDown(self):self.tmp.cleanup()
    def engine(self,outputs):
        self.assertIsNotNone(Learning,'尚未实现网页模型学习流程')
        return Learning(self.store,FakeModel(outputs))
    def test_model_plan_uses_real_article_ids_and_refuses_invented_sources(self):
        e=self.engine([{'article_ids':['invented'],'note':'虚构文章'}])
        with self.assertRaises(ValueError):e.plan('2026-10-26')
        self.assertEqual(self.store.history(),[])
        e=self.engine([{'article_ids':['a'],'note':'先补事务基础'}])
        p=e.plan('2026-10-26');self.assertEqual(p['items'][0]['article_id'],'a');self.assertIn('先补事务',p['note'])
    def test_annotations_persist_and_are_not_marked_mastered(self):
        e=self.engine([])
        n=e.annotate('a','事务原理','note','隔离级别要再看')
        fresh=Store(self.root,self.catalog)
        self.assertEqual(fresh.annotations('a')[0]['note'],'隔离级别要再看')
        self.assertEqual(fresh.read_ids(),[])
        fresh.delete_annotation(n['id']);self.assertEqual(fresh.annotations('a'),[])
    def test_review_requires_actual_checks_and_grades_real_saved_answer(self):
        e=self.engine([])
        with self.assertRaises(ValueError):e.start_review('2026-10-26')
        self.store.generate_plan('2026-10-26');self.store.toggle('2026-10-26','a',True)
        e=self.engine([{'questions':[{'question':'事务有什么作用？','article_ids':['a'],'reference_answer':'并发隔离与原子性','criteria':'说明原子性'}]},
                       {'score':2,'feedback':'主线正确，补充隔离性','follow_up':'隔离级别有哪些？','reference_answer':'事务提供原子性等保证'}])
        review=e.start_review('2026-10-26')
        self.assertNotIn('reference_answer',review['questions'][0])
        qid=review['questions'][0]['id']
        graded=e.answer_review('2026-10-26',qid,'一组操作一起成功或失败')
        self.assertEqual(graded['questions'][0]['answer'],'一组操作一起成功或失败')
        self.assertEqual(graded['questions'][0]['grade']['score'],2)
        # Same answer must not spend a second model call.
        self.assertEqual(e.answer_review('2026-10-26',qid,'一组操作一起成功或失败')['questions'][0]['grade']['score'],2)
    def test_model_failure_does_not_fabricate_completed_review(self):
        self.store.generate_plan('2026-10-26');self.store.toggle('2026-10-26','a',True)
        e=self.engine([{'questions':[{'question':'事务？','article_ids':['a'],'reference_answer':'原子性','criteria':'正确'}]}])
        r=e.start_review('2026-10-26');qid=r['questions'][0]['id']
        with self.assertRaises(IndexError):e.answer_review('2026-10-26',qid,'我的真实回答')
        saved=self.store.review('2026-10-26')
        self.assertEqual(saved['questions'][0]['answer'],'我的真实回答')
        self.assertIsNone(saved['questions'][0].get('grade'))

    def test_short_model_plan_rejected_when_enough_material_exists(self):
        self.store=Store(self.root,[{**self.catalog[0],'id':str(i)} for i in range(6)])
        e=self.engine([{'article_ids':['0'],'note':'too short'}])
        with self.assertRaisesRegex(ValueError,'不足'):e.plan('2026-10-26')
        self.assertIsNone(self.store._load('2026-10-26'))

    def test_weak_checked_article_can_be_assigned_for_remediation(self):
        self.store.replace_plan('2026-10-25',['a']);self.store.toggle('2026-10-25','a',True)
        self.store.save_review('2026-10-25',{'date':'2026-10-25','questions':[{'id':'q','article_ids':['a'],'question':'原理','grade':{'score':0}}]})
        e=self.engine([{'article_ids':['a'],'note':'重读薄弱事务'}])
        p=e.plan('2026-10-26');self.assertEqual(p['items'][0]['article_id'],'a')

    def test_review_supplement_preserves_previous_answers(self):
        c=[self.catalog[0],{**self.catalog[0],'id':'b'}];self.store=Store(self.root,c)
        self.store.replace_plan('2026-10-26',['a','b']);self.store.toggle('2026-10-26','a',True)
        e=self.engine([{'questions':[{'question':'事务？','article_ids':['a'],'reference_answer':'原子性','criteria':'正确'}]},
                       {'questions':[{'question':'补充？','article_ids':['b'],'reference_answer':'原子性','criteria':'正确'}]}])
        r=e.start_review('2026-10-26');qid=r['questions'][0]['id']
        original=self.store.review('2026-10-26');original['questions'][0]['answer']='已经回答';self.store.save_review('2026-10-26',original)
        self.store.toggle('2026-10-26','b',True);r=e.start_review('2026-10-26')
        self.assertEqual(len(r['questions']),2);self.assertEqual(r['questions'][0]['id'],qid)
        self.assertEqual(r['questions'][0]['answer'],'已经回答')

if __name__=='__main__':unittest.main()
