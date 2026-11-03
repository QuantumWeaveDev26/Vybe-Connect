"""Explicit HTTPS reverse-proxy boundary; never trust forwarded origin headers."""
import ipaddress
import os
import re
from dataclasses import dataclass,field
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Deployment:
    production:bool=False
    public_origin:str=''
    authority:str=''
    bind:str='127.0.0.1'
    setup_token:str=field(default='',repr=False)

    def cookie(self,token='',logout=False):
        return 'tw_session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age='+('0' if logout else '43200')+('; Secure' if self.production else '')


def configuration():
    mode=os.environ.get('TW_DEPLOYMENT','local')
    if mode not in ['local','production']:raise ValueError('TW_DEPLOYMENT must be local or production.')
    bind=os.environ.get('TW_BIND','127.0.0.1')
    try:ipaddress.IPv4Address(bind)
    except ValueError:raise ValueError('TW_BIND must be an IPv4 bind address.') from None
    if mode=='local':
        if bind!='127.0.0.1':raise ValueError('Non-loopback binding requires explicit production configuration.')
        return Deployment()
    origin=os.environ.get('TW_PUBLIC_ORIGIN','')
    try:
        parsed=urlsplit(origin);port=parsed.port
        if parsed.scheme!='https' or not parsed.hostname or not re.fullmatch(r'[A-Za-z0-9.-]+',parsed.hostname) or any(c in origin for c in ['@','?','#']) or parsed.path or parsed.query or parsed.fragment or any(ord(c)<=32 for c in origin):raise ValueError()
        if port is not None and not 1<=port<=65535:raise ValueError()
    except ValueError:raise ValueError('Production requires an exact HTTPS TW_PUBLIC_ORIGIN without path, credentials, query or fragment.') from None
    authority=parsed.hostname.lower()+(':'+str(port) if port not in [None,443] else '');canonical='https://'+authority
    return Deployment(True,canonical,authority,bind,os.environ.get('TW_SETUP_TOKEN',''))
