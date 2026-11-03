"""Offline private-data backup/restore. Stop the application before either operation."""
import argparse
import hashlib
import json
import shutil
import sqlite3
from datetime import datetime,timezone
from pathlib import Path
from contextlib import closing


def files(root):
    pending=[root];found=[]
    while pending:
        directory=pending.pop()
        for item in directory.iterdir():
            if item.is_symlink() or getattr(item,'is_junction',lambda:False)():raise ValueError('Data backups do not follow symbolic links or junctions.')
            if item.is_dir():pending.append(item)
            elif item.is_file():found.append(item)
    return sorted(found)


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def healthy(path):
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
        if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Database integrity check failed.')


def backup(source,target):
    source=Path(source).resolve();target=Path(target).resolve()
    if not source.is_dir() or target.exists() or target.is_relative_to(source) or source.is_relative_to(target):raise ValueError('Choose a new backup directory outside the data directory.')
    healthy(source/'teamwave.db');inputs=files(source)
    target.mkdir(parents=True,mode=0o700);payload=target/'payload';payload.mkdir(mode=0o700)
    with closing(sqlite3.connect((source/'teamwave.db').as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(payload/'teamwave.db')) as dst:src.backup(dst)
    for original in inputs:
        relative=original.relative_to(source)
        if relative.as_posix()=='teamwave.db' or relative.as_posix().startswith('teamwave.db-'):continue
        destination=payload/relative;destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700);shutil.copyfile(original,destination);destination.chmod(0o600)
    (payload/'teamwave.db').chmod(0o600);healthy(payload/'teamwave.db')
    manifest={'version':1,'created':datetime.now(timezone.utc).isoformat(),'files':{file.relative_to(payload).as_posix():digest(file) for file in files(payload)}}
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');(target/'manifest.json').chmod(0o600)
    return {'files':len(manifest['files'])}


def restore(source,target):
    source=Path(source).resolve();target=Path(target).resolve()
    if target.exists() or target.is_relative_to(source) or source.is_relative_to(target):raise ValueError('Restore only into a new directory outside the backup.')
    files(source);manifest_file=source/'manifest.json'
    if manifest_file.stat().st_size>1024*1024:raise ValueError('Backup manifest exceeds the supported size.')
    manifest=json.loads(manifest_file.read_text(encoding='utf-8'));expected=manifest.get('files');payload=source/'payload'
    if manifest.get('version')!=1 or not isinstance(expected,dict) or 'teamwave.db' not in expected:raise ValueError('Invalid backup manifest.')
    actual={file.relative_to(payload).as_posix():file for file in files(payload)}
    if set(actual)!=set(expected) or any(digest(file)!=expected[name] for name,file in actual.items()):raise ValueError('Backup file inventory or checksum mismatch.')
    healthy(payload/'teamwave.db');target.mkdir(parents=True,mode=0o700)
    for name,file in actual.items():
        destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700);shutil.copyfile(file,destination);destination.chmod(0o600)
    return {'files':len(actual)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('operation',choices=['backup','restore']);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--target',type=Path,required=True);parser.add_argument('--offline-confirmed',action='store_true');args=parser.parse_args()
    if not args.offline_confirmed:parser.error('Stop the application first and pass --offline-confirmed.')
    print((backup if args.operation=='backup' else restore)(args.source,args.target))
