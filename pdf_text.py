"""PDF extraction in a bounded child process, without provider calls or credentials."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

_slot=threading.BoundedSemaphore(1)


def extract(raw):
    if not isinstance(raw,bytes) or not raw.startswith(b'%PDF-') or len(raw)>1048576:
        raise ValueError('Use a valid text-based PDF up to 1 MiB.')
    if not _slot.acquire(timeout=1):raise ValueError('Another PDF is being processed. Try again shortly.')
    try:
        env={k:os.environ[k] for k in ('PATH','SYSTEMROOT','WINDIR') if k in os.environ}
        env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
        try:
            result=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('pdf_text.py')),'worker'],input=raw,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=8,env=env)
            if result.returncode or len(result.stdout)>600000:raise ValueError()
            value=json.loads(result.stdout)
            if not isinstance(value,dict):raise ValueError()
            text=value.get('text')
            if not isinstance(text,str) or not 1<=len(text.strip())<=120000:raise ValueError()
            return text
        except (OSError,ValueError,subprocess.TimeoutExpired):
            raise ValueError('PDF extraction failed or exceeded its limits. Use an unencrypted text-based PDF with at most 40 pages; scanned images need OCR first.') from None
    finally:_slot.release()


def worker():
    try:
        if os.name!='nt':
            import resource
            resource.setrlimit(resource.RLIMIT_AS,(192*1024*1024,192*1024*1024))
            resource.setrlimit(resource.RLIMIT_CPU,(4,4))
        sys.path.insert(0,str(Path(__file__).resolve().parent/'_vendor'))
        from pypdf import PdfReader
        import io
        raw=sys.stdin.buffer.read(1048577)
        if len(raw)>1048576 or not raw.startswith(b'%PDF-'):raise ValueError()
        reader=PdfReader(io.BytesIO(raw),strict=True)
        if reader.is_encrypted or not 1<=len(reader.pages)<=40:raise ValueError()
        parts=[];length=0
        for page in reader.pages:
            text=page.extract_text() or ''
            text=''.join(c for c in text if ord(c)>=32 or c in '\r\n\t')
            length+=len(text)+1
            if length>120000:raise ValueError()
            parts.append(text)
        text='\n'.join(parts).strip()
        if not text:raise ValueError()
        sys.stdout.buffer.write(json.dumps({'text':text},ensure_ascii=False).encode())
    except Exception:sys.exit(1)


def verify_runtime():
    """In-memory deployment probe: no customer record, file or provider operation."""
    stream=b'BT /F1 12 Tf 20 100 Td (VYBE PDF parser self check) Tj ET'
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
    raw=b'%PDF-1.4\n';offsets=[]
    for number,obj in enumerate(objects,1):
        offsets.append(len(raw));raw+=str(number).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
    start=len(raw);raw+=b'xref\n0 6\n0000000000 65535 f \n'
    raw+=b''.join(f'{offset:010} 00000 n \n'.encode() for offset in offsets)
    raw+=b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+str(start).encode()+b'\n%%EOF\n'
    if extract(raw).strip()!='VYBE PDF parser self check':raise RuntimeError('PDF runtime verification failed.')
    return True


if __name__=='__main__':worker()
