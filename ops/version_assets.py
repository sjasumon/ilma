"""Set immutable asset URLs from their exact bytes; safe to rerun before checks."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def version_assets(root=ROOT):
    root=Path(root);index=root/'static/index.html';worker=root/'static/sw.js'
    original=re.sub(r' data-worker-version="[a-f0-9]+"','',index.read_text());versions={}
    def replace(match):
        path=match[1];file=root/path.lstrip('/')
        if not file.is_file():raise ValueError('Missing referenced asset: '+path)
        version=hashlib.sha256(file.read_bytes()).hexdigest()[:16];versions[path]=version
        return path+'?v=sha256-'+version
    html=re.sub(r'(/static/[^\s\"\'<>?]+\.(?:js|css))\?v=[a-zA-Z0-9_-]+',replace,original)
    if not versions:raise ValueError('No versioned assets found')
    sw=worker.read_text();sw=re.sub(r'(/static/[^\s\"\'<>?]+\.(?:js|css))\?v=[a-zA-Z0-9_-]+',replace,sw)
    worker_logic=re.sub(r"const SHELL = '[^']+';","const SHELL = '';",sw,count=1)
    digest=hashlib.sha256((html+json.dumps(versions,sort_keys=True)+worker_logic).encode()).hexdigest()[:16]
    sw=re.sub(r"const SHELL = '[^']+';", "const SHELL = 'ilma-shell-"+digest+"';",sw,count=1);worker.write_text(sw)
    worker_hash=hashlib.sha256(sw.encode()).hexdigest()[:16]
    html=html.replace('<html ','<html data-worker-version="'+worker_hash+'" ',1)
    index.write_text(html)
    return versions

if __name__=='__main__':
    versions=version_assets();print('Versioned',len(versions),'assets by content hash.')
