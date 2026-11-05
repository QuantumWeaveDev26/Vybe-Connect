"""Refresh local script/style URLs after an asset change."""
import hashlib
import re
from pathlib import Path


def refresh(root):
    index=root/'index.html'
    def version(match):
        attribute,name=match.groups()
        digest=hashlib.sha256((root/name).read_text(encoding='utf-8').encode('utf-8')).hexdigest()[:12]
        return f'{attribute}="/{name}?v={digest}"'
    source=index.read_text(encoding='utf-8')
    index.write_text(re.sub(r'(src|href)="/([^"?]+\.(?:js|css))(?:\?v=[a-zA-Z0-9-]+)?"',version,source),encoding='utf-8')


if __name__=='__main__':refresh(Path(__file__).resolve().parents[1]/'static')
