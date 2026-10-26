"""Bounded public HTTP retrieval; DNS is checked then pinned through TLS."""
import http.client
import ipaddress
import socket
import ssl
import time
import threading
from urllib.parse import urlsplit, urljoin

MAX_BYTES = 8 * 1024 * 1024
TIMEOUT = 12


def validate_url(url):
    if not isinstance(url,str) or len(url)>4096 or any(ord(c)<33 for c in url):
        raise ValueError('网址格式无效')
    try:
        p=urlsplit(url)
        host=p.hostname
        port=p.port or (443 if p.scheme=='https' else 80)
    except ValueError as exc:raise ValueError('网址格式无效') from exc
    if p.scheme not in ('http','https') or not host or p.username is not None or p.password is not None:
        raise ValueError('只支持不带登录信息的 HTTP/HTTPS 公共网址')
    if host.lower().rstrip('.') in ('localhost','localhost.localdomain') or host.lower().endswith(('.localhost','.local','.internal')):
        raise ValueError('不能访问本机或内网地址')
    try: records=socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)
    except OSError as exc:raise ValueError('无法解析公共网址') from exc
    ips=list(dict.fromkeys(r[4][0] for r in records))
    if not ips:raise ValueError('无法解析公共网址')
    for value in ips:
        address=ipaddress.ip_address(value)
        if not address.is_global or (address.version==6 and (address.ipv4_mapped or address.sixtofour or address.teredo)):
            raise ValueError('不能访问本机、内网或云元数据地址')
    target=p.path or '/'
    if p.query:target+='?'+p.query
    return p.scheme,host,port,target,ips


def _request(parts,timeout):
    scheme,host,port,target,ips=parts
    connection=http.client.HTTPConnection(host,port,timeout=timeout)
    sockets=[];guard=threading.Lock();expired=threading.Event()
    def interrupt():
        expired.set()
        with guard:
            if sockets:
                try:sockets[0].shutdown(socket.SHUT_RDWR)
                except OSError:pass
    timer=threading.Timer(timeout,interrupt);timer.daemon=True;timer.start()
    response=None
    def close():
        timer.cancel()
        try:
            if response is not None:response.close()
        finally:
            connection.close()
            with guard:
                if sockets:sockets[0].close()
    try:
        # Only approved IP is connected. A fixed timer covers TLS, headers and body;
        # receiving another byte never extends the original request deadline.
        sock=socket.create_connection((ips[0],port),timeout=timeout)
        with guard:sockets[:]=[sock]
        if expired.is_set():raise TimeoutError()
        if scheme=='https':
            try:
                import certifi
                context=ssl.create_default_context(cafile=certifi.where())
            except ImportError:context=ssl.create_default_context()
            with guard:
                sock=context.wrap_socket(sock,server_hostname=host,do_handshake_on_connect=False)
                sockets[:]=[sock]
            if expired.is_set():raise TimeoutError()
            sock.do_handshake()
        connection.sock=sock
        connection.request('GET',target,headers={'User-Agent':'DailyStudy/1.0 (+public learning resource fetch)','Accept':'text/html,application/rss+xml,application/pdf,text/plain;q=0.9,*/*;q=0.3','Accept-Encoding':'identity'})
        response=connection.getresponse()
        if expired.is_set():raise TimeoutError()
        return response,close
    except (OSError,http.client.HTTPException) as exc:
        close()
        raise ValueError('网页读取超时' if expired.is_set() else '无法读取公共网页') from exc
    except BaseException:
        close();raise


def fetch_public(url,max_bytes=MAX_BYTES,timeout=TIMEOUT):
    started=time.monotonic()
    current=url
    for _ in range(6):
        remaining=timeout-(time.monotonic()-started)
        if remaining<=0:raise ValueError('网页读取超时')
        parts=validate_url(current)
        remaining=timeout-(time.monotonic()-started)
        if remaining<=0:raise ValueError('网页读取超时')
        response,close=_request(parts,remaining)
        try:
            if response.status in (301,302,303,307,308):
                location=response.getheader('Location')
                if not location:raise ValueError('网页重定向缺少目标')
                current=urljoin(current,location)
                continue
            if response.status!=200:raise ValueError('网页返回 HTTP '+str(response.status))
            if response.getheader('Content-Encoding','identity').lower() not in ('','identity'):
                raise ValueError('网页压缩格式不受支持')
            size=response.getheader('Content-Length')
            if size and (not size.isascii() or not size.isdecimal()):raise ValueError('网页长度信息无效')
            expected=int(size) if size else None
            if expected is not None and expected>max_bytes:raise ValueError('网页文件过大')
            chunks=[];total=0
            while True:
                if time.monotonic()-started>timeout:raise ValueError('网页读取超时')
                reader=getattr(response,'read1',response.read)
                chunk=reader(min(65536,max_bytes+1-total))
                if not chunk:break
                total+=len(chunk)
                if total>max_bytes:raise ValueError('网页文件过大')
                chunks.append(chunk)
            if time.monotonic()-started>timeout:raise ValueError('网页读取超时')
            if expected is not None and total!=expected:raise ValueError('网页传输中断，正文不完整')
            return {'url':current,'data':b''.join(chunks),'content_type':response.getheader('Content-Type','text/html')}
        except (OSError,http.client.HTTPException) as exc:
            raise ValueError('网页读取中断或超时') from exc
        finally:close()
    raise ValueError('网页重定向次数过多')
