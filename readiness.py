"""Private operator preflight. No network calls, database writes or secret output."""
import json
import os
import re
from urllib.parse import urlsplit


def setup_details():
    """Field names and activation gates only; never return private values."""
    required={
        'subscription_checkout':['TW_BILLING_KEY_ID','TW_BILLING_KEY_SECRET','TW_BILLING_WEBHOOK_SECRET','TW_BILLING_ACCOUNT_ID','TW_BILLING_PLANS'],
        'platform_ai':['TW_OPENAI_API_KEY','TW_AI_MODEL','TW_PLATFORM_OWNER_EMAIL'],
        'meta_onboarding':['TW_META_PLATFORM_APP_ID','TW_META_PLATFORM_APP_SECRET','TW_META_PLATFORM_CONFIG_ID','TW_META_PLATFORM_VERIFY_TOKEN','TW_META_PLATFORM_VERSION'],
        'recovery_email':['TW_RECOVERY_SECRET','TW_SMTP_HOST','TW_SMTP_FROM'],
        'google_connections':['TW_GOOGLE_CLIENT_ID','TW_GOOGLE_CLIENT_SECRET','TW_CREDENTIAL_KEYS','TW_CREDENTIAL_ACTIVE_KEY'],
    }
    gates={'subscription_checkout':['TW_BILLING_ENABLED','TW_BILLING_ALLOW_LIVE'],
           'platform_ai':['TW_AI_ENABLED','TW_PLATFORM_AI_MANAGED'],
           'meta_onboarding':['TW_META_PLATFORM_ENABLED'],'recovery_email':['TW_RECOVERY_ENABLED'],'google_connections':['TW_GOOGLE_ENABLED']}
    def present(name):
        value=os.environ.get(name,'').strip()
        return bool(value) and not value.upper().startswith(('REPLACE_','YOUR_','ENTER_'))
    result={key:{'missing_fields':[name for name in names if not present(name)],
                 'invalid_fields':[],
                 'disabled_gates':[name for name in gates[key] if os.environ.get(name,'false').lower()!='true'],
                 'live_acceptance':'not_verified'} for key,names in required.items()}
    catalog=os.environ.get('TW_BILLING_PLANS','').strip()
    if catalog:
        from business_providers import plans
        try:
            raw=json.loads(catalog)
            if not isinstance(raw,dict) or not raw or len(plans())!=len(raw):raise ValueError()
        except (ValueError,TypeError):result['subscription_checkout']['invalid_fields'].append('TW_BILLING_PLANS')
    for field,pattern in [('TW_BILLING_KEY_ID',r'rzp_(?:test|live)_[A-Za-z0-9]+'),('TW_BILLING_ACCOUNT_ID',r'acc_[A-Za-z0-9]+')]:
        if present(field) and not re.fullmatch(pattern,os.environ[field]):result['subscription_checkout']['invalid_fields'].append(field)
    if present('TW_CREDENTIAL_KEYS') or present('TW_CREDENTIAL_ACTIVE_KEY'):
        import credential_vault
        try:credential_vault.keys()
        except ValueError:result['google_connections']['invalid_fields'].extend(['TW_CREDENTIAL_KEYS','TW_CREDENTIAL_ACTIVE_KEY'])
    if bool(os.environ.get('TW_SMTP_USERNAME'))!=bool(os.environ.get('TW_SMTP_PASSWORD')):
        result['recovery_email']['missing_fields'].append('TW_SMTP_PASSWORD' if os.environ.get('TW_SMTP_USERNAME') else 'TW_SMTP_USERNAME')
    callbacks={}
    try:
        origin=os.environ.get('TW_PUBLIC_ORIGIN','');p=urlsplit(origin)
        valid=p.scheme=='https' and p.hostname and re.fullmatch(r'[A-Za-z0-9.-]+',p.hostname) and not any((p.path,p.query,p.fragment,p.username,p.password)) and (p.port is None or 1<=p.port<=65535)
        if valid:
            callbacks={'google':origin+'/oauth/google/callback','whatsapp':origin+'/webhook/WORKSPACE_ID','billing':origin+'/razorpay-webhook/billing/WORKSPACE_ID','payments':origin+'/razorpay-webhook/payments/WORKSPACE_ID'}
    except ValueError:pass
    if not callbacks:
        for service in result.values():service['invalid_fields' if os.environ.get('TW_PUBLIC_ORIGIN') else 'missing_fields'].append('TW_PUBLIC_ORIGIN')
    return result,callbacks


def snapshot():
    from business_providers import status, plans
    from embedded_signup import configuration as meta_configuration
    from google_connections import configuration as google_configuration
    from recovery_mail import configuration as mail_configuration

    def configured(check):
        try:return bool(check())
        except (ValueError,TypeError,OSError):return False

    checks={
        'subscription_checkout':configured(lambda: status(None,'billing')['ready'] and plans()),
        'platform_ai':bool(os.environ.get('TW_PLATFORM_AI_MANAGED','false').lower()=='true'
                           and os.environ.get('TW_AI_ENABLED','false').lower()=='true'
                           and os.environ.get('TW_OPENAI_API_KEY')
                           and os.environ.get('TW_AI_MODEL')=='gpt-6-luna'),
        'meta_onboarding':configured(lambda:meta_configuration()['ready']),
        'recovery_email':configured(lambda:mail_configuration()['ready']),
        'google_connections':configured(lambda:google_configuration()['ready'])}
    setup,callbacks=setup_details()
    return {'configuration':{name:'configured' if ready else 'setup_needed' for name,ready in checks.items()},'setup':setup,'callbacks':callbacks,
            'live_acceptance':'not_established',
            'pending_acceptance':['OpenAI inference and agent quality','Razorpay subscription lifecycle',
                                  'Meta approval, onboarding and delivery','Recovery mailbox delivery',
                                  'Payment and shipping operations','Physical devices and off-host disaster recovery'],
            'ready_for_paying_customers':False}


if __name__=='__main__':
    print(json.dumps(snapshot(),indent=2))
    # Configuration alone cannot certify live customer readiness.
    raise SystemExit(2)
