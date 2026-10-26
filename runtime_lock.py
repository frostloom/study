"""Process lifetime guards using each operating system's native facilities."""
from pathlib import Path
import os,sys

class FileLock:
 def __init__(self,path):self.path=Path(path);self.file=None
 def acquire(self):
  self.path.parent.mkdir(parents=True,exist_ok=True);f=self.path.open('a+b')
  try:
   if sys.platform=='win32':
    import msvcrt
    f.seek(0,2)
    if f.tell()==0:f.write(b'\0');f.flush()
    f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
   else:
    import fcntl
    fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  except OSError:
   f.close();raise RuntimeError('已有应用正在使用同一个数据目录，请打开原窗口。') from None
  self.file=f;return self
 def close(self):
  if self.file:self.file.close();self.file=None

def parent_alive(pid):
 if sys.platform=='win32':
  import ctypes
  from ctypes import wintypes
  kernel=ctypes.WinDLL('kernel32',use_last_error=True)
  kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
  kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
  kernel.CloseHandle.argtypes=[wintypes.HANDLE]
  h=kernel.OpenProcess(0x1000,False,pid)
  if not h:return ctypes.get_last_error()==5
  try:
   code=wintypes.DWORD();return bool(kernel.GetExitCodeProcess(h,ctypes.byref(code))) and code.value==259
  finally:kernel.CloseHandle(h)
 try:os.kill(pid,0);return True
 except ProcessLookupError:return False
 except PermissionError:return True
