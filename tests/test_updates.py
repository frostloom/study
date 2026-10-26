import unittest
from updates import UpdateChecker,choose_update,version_tuple

def release(version='1.10.0',name=None,url=None,**kw):
 name=name or f'DailyStudy-{version}-macos-arm64.dmg'
 return dict(tag_name='v'+version,draft=False,prerelease=False,html_url='https://github.com/frostloom/study/releases/tag/v'+version,body='修复并改进阅读体验',assets=[dict(name=name,browser_download_url=url or f'https://github.com/frostloom/study/releases/download/v{version}/{name}')],**kw)
class UpdateTests(unittest.TestCase):
 def test_numeric_version_compare_does_not_misorder_ten(self):
  self.assertGreater(version_tuple('1.10.0'),version_tuple('1.9.9'))
  self.assertIsNone(version_tuple('1.2.3-beta.1'));self.assertIsNone(version_tuple('bad'))
 def test_only_new_matching_stable_release_offered(self):
  self.assertTrue(choose_update(release(),'1.9.0','macos','arm64')['available'])
  for flag in ['draft','prerelease']:
   data=release();data[flag]=True;self.assertFalse(choose_update(data,'1.9.0','macos','arm64')['available'])
  self.assertFalse(choose_update(release(),'1.10.0','macos','arm64')['available'])
  self.assertFalse(choose_update(release(),'1.0.0','windows','x64')['available'])
 def test_github_lookalike_or_unmatched_attachment_never_offered(self):
  for url in ['https://github.com.evil.test/frostloom/study','https://github.com/other/repo/releases/download/v1.10.0/x.dmg','http://github.com/frostloom/study/releases/download/v1.10.0/x.dmg','https://evil.test/x.dmg']:
   self.assertFalse(choose_update(release(url=url),'1.0.0','macos','arm64')['available'])
 def test_windows_selects_setup_when_both_assets_exist(self):
  a='DailyStudy-1.10.0-windows-x64-setup.exe';data=release(name=a)
  data['assets'].append(dict(name='DailyStudy-1.10.0-windows-x64.zip',browser_download_url='https://github.com/frostloom/study/releases/download/v1.10.0/DailyStudy-1.10.0-windows-x64.zip'))
  self.assertTrue(choose_update(data,'1.0.0','windows','x64')['download_url'].endswith('-setup.exe'))
 def test_checks_cached_and_preview_never_calls_network(self):
  calls=[]
  def fetch():calls.append(1);return release()
  checker=UpdateChecker('1.0.0','stable','macos','arm64',fetch=fetch)
  self.assertTrue(checker.check()['available']);self.assertTrue(checker.check()['available']);self.assertEqual(len(calls),1)
  preview=UpdateChecker('1.0.0','preview','macos','arm64',fetch=fetch);self.assertFalse(preview.check()['available']);self.assertEqual(len(calls),1)
 def test_offline_is_nonfatal(self):
  def fetch():raise OSError('offline')
  r=UpdateChecker('1.0.0','stable','macos','arm64',fetch=fetch).check();self.assertFalse(r['available']);self.assertEqual(r['status'],'offline')
