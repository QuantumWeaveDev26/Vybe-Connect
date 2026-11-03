"""Explicitly enabled TLS-only SMTP transport; never expose configuration publicly."""
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlsplit


def configuration():
    enabled=os.environ.get('TW_RECOVERY_ENABLED','false').lower()=='true'
    secret=os.environ.get('TW_RECOVERY_SECRET','');origin=os.environ.get('TW_PUBLIC_ORIGIN','')
    host=os.environ.get('TW_SMTP_HOST','');sender=os.environ.get('TW_SMTP_FROM','')
    security=os.environ.get('TW_SMTP_SECURITY','ssl');username=os.environ.get('TW_SMTP_USERNAME','');password=os.environ.get('TW_SMTP_PASSWORD','')
    valid=False;port=0
    try:
        parsed=urlsplit(origin)
        if parsed.scheme!='https' or not parsed.hostname or not re.fullmatch(r'[A-Za-z0-9.-]+',parsed.hostname) or any(c in origin for c in ['@','?','#']) or parsed.path or any(ord(c)<=32 for c in origin):raise ValueError()
        if parsed.port is not None and not 1<=parsed.port<=65535:raise ValueError()
        origin='https://'+parsed.hostname.lower()+(':'+str(parsed.port) if parsed.port not in [None,443] else '')
        port=int(os.environ.get('TW_SMTP_PORT','465' if security=='ssl' else '587'))
        valid=bool(32<=len(secret)<=256 and not secret.startswith('REPLACE_') and re.fullmatch(r'[A-Za-z0-9.-]{1,253}',host) and re.fullmatch(r'[^\s<>@]{1,100}@[^\s<>@]{1,150}\.[^\s<>@]{1,30}',sender) and security in ['ssl','starttls'] and 1<=port<=65535 and bool(username)==bool(password))
    except (ValueError,TypeError):pass
    return {'ready':enabled and valid,'host':host,'port':port,'sender':sender,'security':security,'username':username,'password':password,'origin':origin,'secret':secret}


def send_recovery(recipient,link):
    cfg=configuration()
    if not cfg['ready']:raise ValueError('Recovery email is disabled or incomplete.')
    if not link.startswith(cfg['origin']+'/#reset='):raise ValueError('Unexpected recovery origin.')
    message=EmailMessage();message['From']=cfg['sender'];message['To']=recipient;message['Subject']='Reset your VYBE Connect password'
    message.set_content('A password reset was requested for your VYBE Connect account.\n\nOpen this link within 15 minutes:\n'+link+'\n\nThis link works once. If you did not request it, ignore this email. Your password has not changed. MFA remains required if enabled.\n')
    context=ssl.create_default_context()
    transport=smtplib.SMTP_SSL if cfg['security']=='ssl' else smtplib.SMTP
    options={'timeout':10}
    if cfg['security']=='ssl':options['context']=context
    with transport(cfg['host'],cfg['port'],**options) as smtp:
        smtp.ehlo()
        if cfg['security']=='starttls':smtp.starttls(context=context);smtp.ehlo()
        if cfg['username']:smtp.login(cfg['username'],cfg['password'])
        if smtp.send_message(message):raise OSError('SMTP recipient was refused.')
