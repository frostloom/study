import unittest
try:
    from catalog import extract_article, split_html_questions
except ImportError:
    extract_article=split_html_questions=None

class CatalogTests(unittest.TestCase):
    def test_complete_article_keeps_last_section_and_excludes_navigation(self):
        self.assertIsNotNone(extract_article,'还未实现完整原文提取')
        html='<aside>导航广告</aside><div class="theme-default-content content__default"><h1>Go</h1><h2 id="base">基础</h2><h3 id="q1">第一题</h3><p>完整答案一</p><h3 id="q2">最后一题</h3><pre>完整代码</pre><p>末尾证据</p></div><footer>页脚</footer>'
        body=extract_article(html)
        self.assertNotIn('导航广告',body);self.assertIn('末尾证据',body)
        parts=split_html_questions(body)
        self.assertEqual(len(parts),2)
        self.assertEqual(parts[1]['anchor'],'q2');self.assertIn('完整代码',parts[1]['content']);self.assertIn('末尾证据',parts[1]['content'])
    def test_missing_article_container_is_not_successful_download(self):
        self.assertIsNotNone(extract_article)
        with self.assertRaises(ValueError):extract_article('<html><h1>404</h1></html>')

if __name__=='__main__':unittest.main()
