"""Shared release identity. User data is independent of application binaries."""
from pathlib import Path
import os,platform,sys

VERSION='1.5.4'
REPOSITORY='frostloom/study'

def default_data_root(channel='stable',system=None,home=None):
 if channel not in ('stable','preview'):raise ValueError('Unknown release channel')
 system=system or sys.platform;explicit_home=home is not None;home=Path(home or Path.home())
 suffix=' Preview' if channel=='preview' else ''
 if system=='win32':
  base=home/'AppData/Local' if explicit_home else Path(os.environ.get('LOCALAPPDATA',home/'AppData/Local'))
  return base/('DailyStudy'+suffix)
 if system=='darwin':return home/'Library/Application Support'/('日常学习'+('预览版' if channel=='preview' else ''))
 return home/'.local/share'/('daily-study-preview' if channel=='preview' else 'daily-study')

def public_info(channel='stable'):
 machine=platform.machine().lower()
 return dict(version=VERSION,channel=channel,platform='windows' if sys.platform=='win32' else 'macos' if sys.platform=='darwin' else 'linux',arch='arm64' if machine in ('arm64','aarch64') else 'x64',repository=REPOSITORY)
