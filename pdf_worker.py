"""Private, one-document subprocess. Never run PDF parsing in the service process."""
import json
from pathlib import Path
import sys

MAX_INPUT=8*1024*1024
MAX_TEXT=2*1024*1024
MAX_STREAM=4*1024*1024
MAX_DECODED=8*1024*1024


class PDFLimitError(BaseException):
    """Do not let the parser's recovery handlers swallow a hard limit."""


def _limits():
    if sys.platform=='win32':
        from process_limits import windows_pdf_limits
        windows_pdf_limits();return
    try:
        import resource
        for kind,limit in ((resource.RLIMIT_CPU,8),(resource.RLIMIT_AS,512*1024*1024),(resource.RLIMIT_DATA,384*1024*1024),(resource.RLIMIT_FSIZE,16*1024*1024),(resource.RLIMIT_NOFILE,64)):
            try:resource.setrlimit(kind,(limit,limit))
            except (ValueError,OSError):pass
    except ImportError:pass


def extract(path):
    _limits()
    from pypdf import PdfReader,Configuration
    from pypdf._configuration import overwrite_configuration
    from pypdf.generic import EncodedStreamObject,DecodedStreamObject
    # These defaults are per private process and cannot interfere with other imports.
    overwrite_configuration(Configuration(maximum_declared_stream_length=MAX_STREAM,array_based_stream_maximum_output_length=MAX_STREAM,zlib_maximum_output_length=MAX_STREAM,lzw_maximum_output_length=MAX_STREAM,run_length_maximum_output_length=MAX_STREAM,brotli_maximum_output_length=MAX_STREAM,jbig2_maximum_output_length=MAX_STREAM,image_maximum_buffer_size=MAX_STREAM,stream_decoding_work_maximum_length=MAX_DECODED,stream_parsing_work_maximum_count=100000,page_tree_maximum_entries=1000,page_tree_maximum_depth=30,xform_maximum_invocations_per_extraction=100,jbig2dec_binary=None,disable_legacy_handling=True))
    seen={};total=0
    def bounded(original):
        def get_data(stream,*args,**kwargs):
            nonlocal total
            value=original(stream,*args,**kwargs)
            if len(value)>MAX_STREAM:raise PDFLimitError('PDF 单个内容流超过安全限制')
            key=id(stream)
            # Retain object references so Python cannot recycle an already-counted id.
            if key not in seen:
                seen[key]=stream;total+=len(value)
                if total>MAX_DECODED:raise PDFLimitError('PDF 解压内容累计超过安全预算')
            return value
        return get_data
    # Cover all decoding, including page contents, XObjects, embedded fonts and CMaps.
    EncodedStreamObject.get_data=bounded(EncodedStreamObject.get_data)
    DecodedStreamObject.get_data=bounded(DecodedStreamObject.get_data)
    source=Path(path)
    if not 0<source.stat().st_size<=MAX_INPUT:raise ValueError('PDF 文件为空或过大')
    reader=PdfReader(source)
    if reader.is_encrypted:raise ValueError('请先解锁加密 PDF')
    if len(reader.pages)>300:raise ValueError('PDF 超过 300 页，请分批导入')
    parts=[];length=0
    for page in reader.pages:
        value=page.extract_text() or '';length+=len(value)
        if length>MAX_TEXT:raise PDFLimitError('PDF 正文过大')
        parts.append(value)
    return '\n\n'.join(parts)


def main(input_path,output_path):
    try:result={'text':extract(input_path)}
    except (Exception,PDFLimitError) as exc:
        result={'error':str(exc)[:300] if isinstance(exc,(ValueError,PDFLimitError)) else 'PDF 无法安全解析或超过资源限制'}
    Path(output_path).write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    return 0


if __name__=='__main__':
    raise SystemExit(main(*sys.argv[1:3]))
