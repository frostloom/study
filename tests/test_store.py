import json
from pathlib import Path
import tempfile
import unittest

try:
    from store import Store
except ImportError:
    Store = None


class StudyStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.catalog = [dict(id=f'a{i}', title=f'完整文章{i}', topic='Go' if i < 8 else 'MySQL',
                             minutes=30, path=f'资料源/{i}.md', source_url='https://example.com/article')
                        for i in range(12)]

    def tearDown(self):
        self.tmp.cleanup()

    def make(self):
        self.assertIsNotNone(Store, '还没有实现持久化学习台')
        return Store(self.root, self.catalog)

    def test_check_survives_restart_and_same_day_plan_refresh(self):
        s = self.make(); p = s.generate_plan('2026-10-26')
        aid = p['items'][0]['article_id']
        s.toggle('2026-10-26', aid, True)
        restarted = Store(self.root, self.catalog)
        p2 = restarted.generate_plan('2026-10-26')
        self.assertEqual(p['id'], p2['id'])
        self.assertTrue(next(i for i in p2['items'] if i['article_id'] == aid)['done'])
        restarted.toggle('2026-10-26', aid, False)
        self.assertFalse(restarted.handoff('2026-10-26')['completed'])

    def test_unfinished_rollover_is_bounded_and_completed_not_assigned_as_new(self):
        s = self.make(); first = s.generate_plan('2026-10-26')
        aid = first['items'][0]['article_id']; s.toggle('2026-10-26', aid, True)
        second = s.generate_plan('2026-10-27')
        self.assertLessEqual(sum(i['minutes'] for i in second['items']), 120)
        ids = [i['article_id'] for i in second['items']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn(aid, ids)
        carried = [i for i in second['items'] if i['kind'] == 'carry']
        self.assertTrue(carried)
        self.assertLessEqual(sum(i['minutes'] for i in carried), 60)
        self.assertEqual(second['review_minutes'], 60)

    def test_handoff_contains_only_checked_articles_and_keeps_date_history(self):
        s = self.make(); a = s.generate_plan('2026-10-26')['items'][0]['article_id']
        self.assertEqual(s.handoff('2026-10-26')['completed'], [])
        s.toggle('2026-10-26', a, True)
        s.generate_plan('2026-10-27')
        h = s.handoff('2026-10-26')
        self.assertEqual([i['id'] for i in h['completed']], [a])
        self.assertEqual(h['assessment_status'], '待网页AI复习')
        self.assertNotIn('score', h)
        exported = json.loads((self.root/'学习台/data/复习交接/2026-10-26.json').read_text(encoding='utf-8'))
        self.assertEqual(exported['completed'][0]['id'], a)

    def test_invalid_day_and_unplanned_article_do_not_change_history(self):
        s = self.make(); s.generate_plan('2026-10-26')
        for day in ['../other', '2026-02-30', '2026-1-1']:
            with self.assertRaises(ValueError): s.generate_plan(day)
        with self.assertRaises(ValueError): s.toggle('2026-10-26', 'a999', True)
        self.assertEqual(s.handoff('2026-10-26')['completed'], [])

    def test_manual_add_can_start_a_day_without_ai(self):
        s = self.make()
        plan=s.add_article('2026-10-26','a0')
        self.assertEqual([x['article_id'] for x in plan['items']],['a0'])
        self.assertFalse(plan['items'][0]['done'])

    def test_replanning_cannot_silently_drop_a_checked_item(self):
        s = self.make(); p = s.generate_plan('2026-10-26')
        aid = p['items'][0]['article_id']; s.toggle('2026-10-26', aid, True)
        remaining = [a['id'] for a in self.catalog if a['id'] != aid][:2]
        with self.assertRaises(ValueError): s.replace_plan('2026-10-26', remaining)
        self.assertEqual(s.handoff('2026-10-26')['completed'][0]['id'], aid)

if __name__ == '__main__': unittest.main()
