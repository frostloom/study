"""Run an isolated development preview, never the daily learning data root."""
from pathlib import Path
import os,subprocess,sys
root=Path(__file__).resolve().parents[1]
os.chdir(root)
sys.path.insert(0,str(root))
from app_info import default_data_root
if __name__=='__main__':
 print('开发预览数据：'+str(default_data_root('preview')),flush=True)
 subprocess.run([sys.executable,str(root/'backend_entry.py'),'--channel','preview','--no-legacy'],check=True)
