"""Windows equivalent of the isolated PDF worker's Unix CPU/memory ceiling."""
_job=None

def windows_pdf_limits():
 import ctypes
 from ctypes import wintypes
 class Basic(ctypes.Structure):
  _fields_=[('process_time',ctypes.c_longlong),('job_time',ctypes.c_longlong),('flags',wintypes.DWORD),('min_working',ctypes.c_size_t),('max_working',ctypes.c_size_t),('active',wintypes.DWORD),('affinity',ctypes.c_size_t),('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]
 class IO(ctypes.Structure):_fields_=[(x,ctypes.c_ulonglong) for x in ['read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes']]
 class Extended(ctypes.Structure):_fields_=[('basic',Basic),('io',IO),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
 k=ctypes.WinDLL('kernel32',use_last_error=True)
 k.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR];k.CreateJobObjectW.restype=wintypes.HANDLE
 k.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD];k.SetInformationJobObject.restype=wintypes.BOOL
 k.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE];k.AssignProcessToJobObject.restype=wintypes.BOOL
 k.GetCurrentProcess.restype=wintypes.HANDLE;k.CloseHandle.argtypes=[wintypes.HANDLE]
 job=k.CreateJobObjectW(None,None);info=Extended();info.basic.flags=0x2|0x100;info.basic.process_time=8*10_000_000;info.process_memory=512*1024*1024
 if not job or not k.SetInformationJobObject(job,9,ctypes.byref(info),ctypes.sizeof(info)) or not k.AssignProcessToJobObject(job,k.GetCurrentProcess()):
  if job:k.CloseHandle(job)
  raise ValueError('无法对 PDF 解析设置资源限制，请重启应用后重试')
 global _job
 _job=job
