"""Authenticated encryption for workspace credential files; keys stay outside data."""
import base64
import json
import os
import re


class VaultError(ValueError):
    pass


def keys():
    raw=os.environ.get('TW_CREDENTIAL_KEYS','')
    active=os.environ.get('TW_CREDENTIAL_ACTIVE_KEY','')
    if not raw and not active:return None
    try:
        ring=json.loads(raw)
        if not isinstance(ring,dict) or not 1<=len(ring)<=8:raise ValueError()
        decoded={}
        for name,value in ring.items():
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',name) or not isinstance(value,str):raise ValueError()
            key=base64.b64decode(value,validate=True)
            if len(key)!=32:raise ValueError()
            decoded[name]=key
        if active not in decoded:raise ValueError()
        return active,decoded
    except (ValueError,TypeError):raise VaultError('Credential encryption configuration is invalid.') from None


def aad(tenant,kind):
    if not re.fullmatch(r'[a-f0-9]{16}',tenant) or kind not in ('meta','ai'):raise VaultError('Invalid credential scope.')
    return ('vybe-credentials:v1:'+kind+':'+tenant).encode()


def seal(value,tenant,kind):
    binding=aad(tenant,kind)
    if not isinstance(value,dict) or value.get('tenant')!=tenant:raise VaultError('Invalid credential scope.')
    ring=keys()
    if ring is None:return value
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    active,decoded=ring
    nonce=os.urandom(12)
    ciphertext=AESGCM(decoded[active]).encrypt(nonce,json.dumps(value,separators=(',',':')).encode(),binding)
    return {'vault':1,'key':active,'nonce':base64.b64encode(nonce).decode(),'ciphertext':base64.b64encode(ciphertext).decode()}


def unseal(value,tenant,kind,legacy=False):
    binding=aad(tenant,kind);ring=keys()
    if not isinstance(value,dict):raise VaultError('Credential storage is unavailable.')
    if 'vault' not in value:
        if ring is not None and not legacy:raise VaultError('Credential migration is required.')
        if value.get('tenant')!=tenant:raise VaultError('Invalid credential scope.')
        return value
    try:
        if ring is None or value.get('vault')!=1:raise ValueError()
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce=base64.b64decode(value['nonce'],validate=True)
        if len(nonce)!=12:raise ValueError()
        plain=AESGCM(ring[1][value['key']]).decrypt(nonce,base64.b64decode(value['ciphertext'],validate=True),binding)
        result=json.loads(plain)
        if not isinstance(result,dict) or result.get('tenant')!=tenant:raise ValueError()
        return result
    except Exception:raise VaultError('Credential storage is unavailable.') from None
