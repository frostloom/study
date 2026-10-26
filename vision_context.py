"""Bounded source images for local context preparation and multimodal requests."""
import base64,binascii,hashlib,re
from pathlib import Path
from urllib.parse import urljoin,urlsplit,unquote,unquote_to_bytes
from concurrent.futures import ThreadPoolExecutor
from safe_web import fetch_public
MAX_IMAGES=4
MAX_IMAGE_BYTES=3*1024*1024
MAX_TOTAL_BYTES=6*1024*1024

def image_type(data,svg=False):
 if data.startswith(b'\x89PNG\r\n\x1a\n'):return 'image/png'
 if data.startswith(b'\xff\xd8\xff'):return 'image/jpeg'
 if data.startswith((b'GIF87a',b'GIF89a')):return 'image/gif'
 if data[:4]==b'RIFF' and data[8:12]==b'WEBP':return 'image/webp'
 if svg and re.search(br'<svg\b',data[:2000],re.I):return 'image/svg+xml'
 raise ValueError('不是支持的图片格式')

def data_image(value,allow_svg=False):
 if not isinstance(value,str) or len(value)>MAX_IMAGE_BYTES*4//3+200:raise ValueError('图片过大')
 m=re.fullmatch(r'data:(image/[a-zA-Z0-9.+-]+)(;base64)?,(.*)',value,re.S)
 if not m:raise ValueError('图片需为有效data URL')
 try:data=base64.b64decode(m[3],validate=True) if m[2] else unquote_to_bytes(m[3])
 except (ValueError,binascii.Error):raise ValueError('图片编码无效') from None
 if not data or len(data)>MAX_IMAGE_BYTES:raise ValueError('图片为空或超过3MB')
 mime=image_type(data,allow_svg)
 if mime!=m[1].lower():raise ValueError('图片内容与格式不一致')
 return data,mime

def validate_images(images):
 if images is None:return []
 if not isinstance(images,list) or len(images)>MAX_IMAGES:raise ValueError('每次最多附带4张当前小节图片')
 total=0;result=[]
 for item in images:
  if not isinstance(item,dict):raise ValueError('图片格式无效')
  data,mime=data_image(item.get('data_url'));total+=len(data)
  if total>MAX_TOTAL_BYTES:raise ValueError('本次图片合计超过6MB，请缩小范围')
  result.append(dict(data_url='data:'+mime+';base64,'+base64.b64encode(data).decode(),alt=str(item.get('alt',''))[:500],source_id=str(item.get('source_id',''))[:64]))
 return result

def source_id(src):return hashlib.sha256(src.encode()).hexdigest()

def _source_image(root,article,item):
 src=item['src'];mime=''
 if src.startswith('data:'):data,mime=data_image(src,allow_svg=True)
 else:
  parsed=urlsplit(src);local=None
  if not parsed.scheme and not parsed.netloc and not src.startswith('/'):
   article_path=Path(article['path']);parts=article_path.parts
   base=root/Path(*parts[:2]) if len(parts)>2 and parts[0]=='资料源' else root/Path(*parts[:3]) if len(parts)>3 and parts[:2]==('学习台','imports') else (root/article_path).parent
   path=((root/article_path).parent/unquote(parsed.path)).resolve()
   if path.is_relative_to(base.resolve()) and path.is_relative_to(root) and path.is_file():local=path
   elif '..' in Path(unquote(parsed.path)).parts:raise ValueError('图片超出当前资料目录')
  if local:
   if local.stat().st_size>MAX_IMAGE_BYTES:raise ValueError('原图超过3MB')
   data=local.read_bytes()
  else:
   url=urljoin(article.get('source_url',''),src)
   data=fetch_public(url,max_bytes=MAX_IMAGE_BYTES)['data']
  mime=image_type(data,svg=True)
 return dict(data_url='data:'+mime+';base64,'+base64.b64encode(data).decode(),alt=item.get('alt','')[:500],source_id=source_id(src))

def prepare_images(root,article,images):
 root=Path(root).resolve();unique=list({x['src']:x for x in images if x.get('src')}.values());warnings=[];prepared=[];total=0
 def get(item):
  try:return _source_image(root,article,item),None
  except (ValueError,OSError,RuntimeError):return None,'图片未能读取：'+(item.get('alt') or '未命名插图')[:120]
 with ThreadPoolExecutor(max_workers=MAX_IMAGES) as pool:
  for img,error in pool.map(get,unique[:MAX_IMAGES]):
   if error:warnings.append(error);continue
   data,_=data_image(img['data_url'],allow_svg=True);total+=len(data)
   if total>MAX_TOTAL_BYTES:warnings.append('图片合计过大，请缩小到更细的小节');continue
   prepared.append(img)
 if len(unique)>MAX_IMAGES:warnings.append(f'本小节共{len(unique)}张图，本次最多带前4张；可选更细的小节提问')
 return dict(images=prepared,warnings=warnings,total_images=len(unique),failed_images=min(len(unique),MAX_IMAGES)-len(prepared))
