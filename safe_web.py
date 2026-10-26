"""Bounded public HTTP retrieval; DNS is checked then pinned through TLS."""
import http.client
import ipaddress
import socket
import ssl
import time
import threading
import urllib.request
import base64
from urllib.parse import urlsplit, urljoin,unquote,quote

MAX_BYTES = 8 * 1024 * 1024
TIMEOUT = 30

class FetchError(ValueError):
    """A transient public-network failure that may be retried within one deadline."""



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
    target=quote(p.path or '/',safe="/%:@!$&'()*+,;=-._~")
    if p.query:target+='?'+quote(p.query,safe="%:@!$&'()*+,;=/?-._~")
    return p.scheme,host,port,target,ips


def _system_proxy(host,scheme):
    # Only local user/OS settings select a proxy. URLs cannot supply one.
    try:
        if urllib.request.proxy_bypass(host):return None
        value=urllib.request.getproxies().get(scheme)
        if not value:return None
        proxy=urlsplit(value if '://' in value else 'http://'+value)
        if proxy.scheme!='http' or not proxy.hostname:return None
        headers={}
        if proxy.username is not None:
            token=(unquote(proxy.username)+':'+unquote(proxy.password or '')).encode('utf-8')
            headers['Proxy-Authorization']='Basic '+base64.b64encode(token).decode('ascii')
        return proxy.hostname,proxy.port or 80,headers
    except (OSError,ValueError,TypeError):return None


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
        began=time.monotonic();last=None;sock=None;proxy=_system_proxy(host,scheme)
        for ip in ips:
            remaining=timeout-(time.monotonic()-began)
            if remaining<=0 or expired.is_set():raise TimeoutError()
            trial=None
            try:
                trial=socket.create_connection((proxy[0],proxy[1]) if proxy else (ip,port),timeout=min(4,remaining))
                with guard:sockets[:]=[trial]
                if proxy:
                    authority=('['+ip+']' if ':' in ip else ip)+':'+str(port)
                    headers={'Host':authority,**proxy[2]}
                    connect='CONNECT '+authority+' HTTP/1.1\r\n'+''.join(k+': '+v+'\r\n' for k,v in headers.items())+'\r\n'
                    trial.sendall(connect.encode('ascii'))
                    response_proxy=http.client.HTTPResponse(trial)
                    try:
                        response_proxy.begin()
                        if response_proxy.status!=200:raise OSError('Configured proxy rejected connection')
                    finally:response_proxy.close()
                if scheme=='https':
                    try:
                        import certifi
                        context=ssl.create_default_context(cafile=certifi.where())
                    except ImportError:context=ssl.create_default_context()
                    trial=context.wrap_socket(trial,server_hostname=host,do_handshake_on_connect=False)
                    with guard:sockets[:]=[trial]
                    trial.settimeout(min(6,max(.01,timeout-(time.monotonic()-began))))
                    trial.do_handshake()
                trial.settimeout(max(.01,timeout-(time.monotonic()-began)))
                sock=trial;break
            except (OSError,http.client.HTTPException) as exc:
                last=exc
                if trial is not None:trial.close()
                with guard:sockets.clear()
        if sock is None:raise last or TimeoutError()
        if expired.is_set():raise TimeoutError()
        connection.sock=sock
        connection.request('GET',target,headers={'User-Agent':'DailyStudy/1.0 (+public learning resource fetch)','Accept':'text/html,application/rss+xml,application/pdf,text/plain;q=0.9,*/*;q=0.3','Accept-Encoding':'identity'})
        response=connection.getresponse()
        if expired.is_set():raise TimeoutError()
        return response,close
    except (OSError,http.client.HTTPException) as exc:
        close()
        raise FetchError('网页读取超时' if expired.is_set() else '无法读取公共网页') from exc
    except BaseException:
        close();raise


def _fetch_once(url,max_bytes=MAX_BYTES,timeout=TIMEOUT,offset=0):
    started=time.monotonic()
    current=url
    for _ in range(6):
        remaining=timeout-(time.monotonic()-started)
        if remaining<=0:raise FetchError('网页读取超时')
        parts=validate_url(current)
        if offset and len(parts[4])>1:parts=(*parts[:4],parts[4][offset:]+parts[4][:offset])
        remaining=timeout-(time.monotonic()-started)
        if remaining<=0:raise FetchError('网页读取超时')
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
                if time.monotonic()-started>timeout:raise FetchError('网页读取超时')
                reader=getattr(response,'read1',response.read)
                chunk=reader(min(65536,max_bytes+1-total))
                if not chunk:break
                total+=len(chunk)
                if total>max_bytes:raise ValueError('网页文件过大')
                chunks.append(chunk)
            if time.monotonic()-started>timeout:raise FetchError('网页读取超时')
            if expected is not None and total!=expected:raise FetchError('网页传输中断，正文不完整')
            return {'url':current,'data':b''.join(chunks),'content_type':response.getheader('Content-Type','text/html')}
        except (OSError,http.client.HTTPException) as exc:
            raise FetchError('网页读取中断或超时') from exc
        finally:close()
    raise ValueError('网页重定向次数过多')


def fetch_public(url,max_bytes=MAX_BYTES,timeout=TIMEOUT):
    started=time.monotonic();last=None
    for attempt in range(2):
        remaining=timeout-(time.monotonic()-started)
        if remaining<=0:break
        try:return _fetch_once(url,max_bytes,min(18,remaining),offset=attempt)
        except FetchError as exc:last=exc
    raise FetchError('网页读取超时或中断，请重试或打开原文。') from last
