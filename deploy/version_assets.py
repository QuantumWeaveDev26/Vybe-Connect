"""Refresh local script/style URLs after an asset change."""
import hashlib
import json
import re
from pathlib import Path


def refresh(root):
    index=root/'index.html'
    def version(match):
        attribute,name=match.groups()
        digest=hashlib.sha256((root/name).read_text(encoding='utf-8').encode('utf-8')).hexdigest()[:12]
        return f'{attribute}="/{name}?v={digest}"'
    source=index.read_text(encoding='utf-8')
    def manifest_version(match):
        paths=json.loads(match.group(1))
        paths=[re.sub(r'\?v=[^&]+$', '?v='+hashlib.sha256((root/path.split('?')[0].lstrip('/')).read_text(encoding='utf-8').encode('utf-8')).hexdigest()[:12],path) for path in paths]
        return '<script type="application/json" id="workspace-scripts">'+json.dumps(paths,separators=(',',':'))+'</script>'
    source=re.sub(r'<script type="application/json" id="workspace-scripts">(.*?)</script>',manifest_version,source)
    index.write_text(re.sub(r'(src|href)="/([^"?]+\.(?:js|css))(?:\?v=[a-zA-Z0-9-]+)?"',version,source),encoding='utf-8')


if __name__=='__main__':refresh(Path(__file__).resolve().parents[1]/'static')
