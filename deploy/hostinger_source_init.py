"""Pinned-source initializer for an official Python container, without Git builds."""
import hashlib
import io
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path,PurePosixPath

COMMIT='10dc705ac18afa7d4982127d84affa55d5523e0b'
ARCHIVE_SHA256='f98b8e5c4f02efadd773d1dc8c37e1ddfe1a68a3d4c859437ba81999df061a57'
ARCHIVE_URL='https://codeload.github.com/QuantumWeaveDev26/Vybe-Connect/zip/'+COMMIT
ARCHIVE_ROOT='Vybe-Connect-'+COMMIT


def unpack(data,destination,digest=ARCHIVE_SHA256,prefix=ARCHIVE_ROOT):
    if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Release archive checksum mismatch.')
    destination=Path(destination).resolve()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if sum(i.file_size for i in archive.infolist())>25*1024*1024:raise ValueError('Release archive is oversized.')
        for item in archive.infolist():
            parts=PurePosixPath(item.filename).parts
            if not parts or parts[0]!=prefix or '..' in parts or '\\' in item.filename or stat.S_ISLNK(item.external_attr>>16):raise ValueError('Unsafe release archive member.')
            if len(parts)==1:continue
            target=destination.joinpath(*parts[1:]);target.resolve().relative_to(destination)
            if item.is_dir():target.mkdir(parents=True,exist_ok=True)
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                with archive.open(item) as source,target.open('wb') as output:shutil.copyfileobj(source,output)
                target.chmod(0o644)
    if not (destination/'server.py').is_file() or not (destination/'static/index.html').is_file():raise ValueError('Release entry points are missing.')


def initialize():
    active=Path('/data/active')
    if not active.exists():active.mkdir(parents=True,mode=0o700)
    os.chown(active,10001,10001)
    root=Path('/source');root.mkdir(parents=True,exist_ok=True)
    release=root/COMMIT;marker=release/'.archive-sha256'
    if release.is_dir() and marker.is_file() and marker.read_text().strip()==ARCHIVE_SHA256 and (release/'server.py').is_file():
        print('Pinned VYBE Connect release is ready.',flush=True);return
    # Docker may create working directories while preparing a dependent container.
    if release.exists():
        if release.is_dir() and not any(release.iterdir()):release.rmdir()
        else:raise ValueError('Existing release does not match the expected marker; refusing overwrite.')
    request=urllib.request.Request(ARCHIVE_URL,headers={'User-Agent':'VYBE-Connect-pinned-release'})
    with urllib.request.urlopen(request,timeout=30) as response:data=response.read(5*1024*1024+1)
    if len(data)>5*1024*1024:raise ValueError('Release download is oversized.')
    staging=Path(tempfile.mkdtemp(prefix='release-',dir=root))
    try:
        unpack(data,staging)
        subprocess.run([sys.executable,'-m','pip','install','--disable-pip-version-check','--no-cache-dir','--only-binary=:all:','--require-hashes','--target',str(staging/'_vendor'),'-r',str(staging/'requirements-runtime.txt')],check=True,env=dict(os.environ,TMPDIR=str(staging)))
        (staging/'.archive-sha256').write_text(ARCHIVE_SHA256+'\n');staging.chmod(0o755)
        staging.rename(release)
    finally:
        if staging.exists():shutil.rmtree(staging)
    print('Verified VYBE Connect release initialized.',flush=True)


if __name__=='__main__':initialize()
