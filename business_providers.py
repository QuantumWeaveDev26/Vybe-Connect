"""Explicit Razorpay/Shiprocket adapters; credentials and activation stay server-side."""
import base64
import json
import os
import re
from provider_transport import request, RemoteError


def config(tenant, provider):
    prefix = ('TW_BILLING_' if provider == 'billing' else 'TW_' + provider.upper() + '_' + tenant.upper() + '_')
    keys = ['KEY_ID','KEY_SECRET','WEBHOOK_SECRET','ACCOUNT_ID','ENABLED','ALLOW_LIVE'] if provider in ('payments','billing') else ['TOKEN','ENABLED','PICKUP_LOCATION','PICKUP_POSTCODE']
    return dict(prefix=prefix, **{key: os.environ.get(prefix + key, '') for key in keys})


def status(tenant, provider):
    c = config(tenant, provider)
    required = ['KEY_ID','KEY_SECRET','WEBHOOK_SECRET','ACCOUNT_ID'] if provider != 'shipping' else ['TOKEN','PICKUP_LOCATION','PICKUP_POSTCODE']
    present = {key: bool(c[key]) for key in required}
    allowed = provider == 'shipping' or c['KEY_ID'].startswith('rzp_test_') or c['ALLOW_LIVE'].lower() == 'true'
    return {'provider': 'Shiprocket' if provider == 'shipping' else 'Razorpay', 'prefix': c['prefix'],
            'present': present, 'configured': all(present.values()), 'enabled': c['ENABLED'].lower() == 'true',
            'ready': all(present.values()) and c['ENABLED'].lower() == 'true' and allowed,
            'mode': 'test' if provider != 'shipping' and c['KEY_ID'].startswith('rzp_test_') else 'live',
            'verification': 'not_verified'}


def razorpay(tenant, scope, method, edge, payload=None):
    if scope not in ('payments','billing') or not re.fullmatch(r'[a-z_]+(?:/[A-Za-z0-9_]+){0,2}', edge):
        raise RemoteError('Invalid Razorpay operation.', True)
    if not status(tenant, scope)['ready']: raise RemoteError('Configure and explicitly enable this Razorpay connection first.', True)
    c = config(tenant, scope)
    authorization = base64.b64encode((c['KEY_ID'] + ':' + c['KEY_SECRET']).encode()).decode()
    return request('https://api.razorpay.com/v1/' + edge, method, payload, {'Authorization':'Basic ' + authorization})


def shiprocket(tenant, method, edge, payload=None, query=None):
    if not re.fullmatch(r'[a-z0-9_/]+', edge): raise RemoteError('Invalid shipping operation.', True)
    if not status(tenant, 'shipping')['ready']: raise RemoteError('Configure and explicitly enable Shiprocket first.', True)
    from urllib.parse import urlencode
    url='https://apiv2.shiprocket.in/v1/external/'+edge+('?' + urlencode(query) if query else '')
    return request(url, method, payload,
                   {'Authorization':'Bearer ' + config(tenant, 'shipping')['TOKEN']})


def plans():
    try: values = json.loads(os.environ.get('TW_BILLING_PLANS', '{}'))
    except ValueError: return {}
    if not isinstance(values, dict): return {}
    return {key: value for key, value in values.items() if re.fullmatch(r'[a-z0-9_-]{1,40}', key) and isinstance(value, dict)
            and re.fullmatch(r'plan_[A-Za-z0-9]+', str(value.get('plan_id','')))
            and isinstance(value.get('name'), str) and 1 <= len(value['name']) <= 80
            and type(value.get('amount_minor')) is int and 0 < value['amount_minor'] < 100000000
            and value.get('currency') == 'INR' and value.get('interval') in ('monthly','yearly')
            and type(value.get('cycles',12)) is int and 1 <= value.get('cycles',12) <= 120}
