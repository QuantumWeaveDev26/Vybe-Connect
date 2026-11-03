"""Offline server-operator password recovery. Never accept passwords as CLI arguments."""
import argparse
import getpass
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from store import Store,Problem


def existing_store(path,email):
    path=Path(path).resolve()
    if not path.is_file():raise ValueError('An existing application database is required; no database was created.')
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
        if not db.execute('SELECT 1 FROM users WHERE email=?',(email.strip().lower(),)).fetchone():raise ValueError('Account not found; no account was created.')
    return Store(path)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--db',type=Path,required=True);parser.add_argument('--email',required=True);parser.add_argument('--offline-confirmed',action='store_true');args=parser.parse_args()
    if not args.offline_confirmed:parser.error('Stop the app, preserve a backup and pass --offline-confirmed.')
    try:
        store=existing_store(args.db,args.email)
        if not sys.stdin.isatty():raise ValueError('An interactive terminal is required; no passwords were read.')
        password=getpass.getpass('New account password: ');confirmation=getpass.getpass('Confirm new password: ')
        if password!=confirmation:raise ValueError('Passwords did not match. Nothing changed.')
        store.operator_reset_password(args.email,password)
    except (ValueError,Problem,sqlite3.Error):raise SystemExit('Recovery failed. Check the account, database and password requirements; nothing was printed.')
    print('Password replaced. All sessions for this account were revoked. Roles and memberships are unchanged.')
