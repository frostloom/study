"""Collect actual runtime distribution licenses, never app data."""
from pathlib import Path
import importlib.metadata as metadata,sys,sysconfig,shutil
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
for name in ['pyinstaller','certifi','pypdf','tzdata']:
 dist=metadata.distribution(name)
 for rel in dist.files or []:
  if any(x in str(rel).lower() for x in ['license','copying','copyright']):
   p=Path(dist.locate_file(rel))
   if p.is_file():dest=out/name/str(rel);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
for p in [Path(sysconfig.get_path('stdlib'))/'LICENSE.txt',Path(sys.base_prefix)/'LICENSE.txt']:
 if p.is_file():shutil.copy2(p,out/'Python-LICENSE.txt')
