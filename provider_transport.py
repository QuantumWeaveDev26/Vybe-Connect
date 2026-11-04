"""Bounded TLS JSON requests to fixed provider origins. No redirects or retries."""
import json
import urllib.request
import urllib.error


class RemoteError(Exception):
    def __init__(self, message, definitive=False):
        super().__init__(message)
        self.definitive = definitive


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None


def request(url, method='GET', payload=None, headers=None):
    allowed = ('https://api.razorpay.com/v1/', 'https://apiv2.shiprocket.in/v1/external/', 'https://graph.facebook.com/', 'https://api.openai.com/v1/models/')
    if not any(url.startswith(origin) for origin in allowed):
        raise RemoteError('Unsupported provider destination.', True)
    req = urllib.request.Request(url, method=method,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers=dict({'Content-Type': 'application/json', 'Accept': 'application/json'}, **(headers or {})))
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=25) as response:
            data = response.read(1024 * 1024 + 1)
        if len(data) > 1024 * 1024: raise ValueError()
        result = json.loads(data)
        if not isinstance(result, dict): raise ValueError()
        return result
    except urllib.error.HTTPError as error:
        # Do not retain provider bodies, URLs, credentials, or customer details.
        raise RemoteError('Provider returned HTTP ' + str(error.code) + '.', 400 <= error.code < 500 and error.code not in (408, 429)) from None
    except (OSError, ValueError, urllib.error.URLError):
        raise RemoteError('Provider outcome is uncertain. Reconcile before retrying.') from None
