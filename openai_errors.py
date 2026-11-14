"""Safe OpenAI error classification and bounded account-wide request cooldowns."""
import hashlib
import json
import threading
import time

_blocked = {}
_lock = threading.Lock()


class OpenAIRequestError(ValueError):
    def __init__(self, message, status, reason, retry_after=0):
        super().__init__(message)
        self.http_status = status
        self.reason = reason
        self.retry_after = retry_after


def identity(key):
    return hashlib.sha256(key.encode()).hexdigest()


def pause_status(key):
    """Return only safe, current cooldown metadata; never send a provider request."""
    with _lock:
        entry = _blocked.get(identity(key))
        if entry and entry[0] > time.monotonic():
            return {'reason':entry[1].reason,'retry_after':max(1,int(entry[0]-time.monotonic()))}
        _blocked.pop(identity(key), None)
    return None


def ensure_available(key):
    with _lock:
        entry = _blocked.get(identity(key))
        if entry and entry[0] > time.monotonic():
            raise OpenAIRequestError(str(entry[1]), entry[1].http_status, entry[1].reason,
                                     max(1, int(entry[0]-time.monotonic())))
        _blocked.pop(identity(key), None)


def http_failure(error, key, background=False):
    # Never surface raw provider messages, customer input, keys or request URLs.
    body = {}
    try:
        parsed = json.loads(error.read(8192))
        if isinstance(parsed, dict) and isinstance(parsed.get('error'), dict):
            body = parsed['error']
    except (ValueError, OSError, TypeError, AttributeError):
        pass
    code, kind = body.get('code'), body.get('type')
    status = error.code
    reason, wait = 'provider_error', 0
    prefix = ('OpenAI background request returned HTTP ' if background else 'OpenAI returned HTTP ')+str(status)+'. '
    hint = 'Check provider access. No automatic retry was attempted.'
    if status == 429:
        quota = kind == 'insufficient_quota' or code in (
            'insufficient_quota', 'credit_balance_exhausted', 'organization_spend_limit_exceeded',
            'organization_usage_limit_exceeded', 'billing_hard_limit_reached')
        rate = kind == 'rate_limit_error' or code in ('rate_limit_exceeded','slow_down')
        reason = 'quota_exhausted' if quota else 'rate_limited' if rate else 'quota_or_rate_limit'
        wait = 900 if quota else 60
        try:
            wait = max(wait, min(3600, max(1, int(float(error.headers.get('Retry-After','0'))))))
        except (ValueError, TypeError, AttributeError, OverflowError):
            pass
        hint = ('API credits or an account spending/usage limit are blocking AI. The platform owner must review OpenAI billing and limits.'
                if quota else 'OpenAI is rate limiting this account. Requests are paused briefly; try again later.'
                if rate else 'OpenAI rejected this account for quota or rate limits. The platform owner must check API billing and limits.')
        hint += ' No response was generated and no automatic retry will be sent.'
    elif status in (401,403):
        reason = 'access_denied'
        hint = 'The platform owner must check the API key, project and model permissions. No automatic retry was attempted.'
    elif status == 404:
        reason = 'model_unavailable'
        hint = 'The configured model is unavailable to this API project. No automatic retry was attempted.'
    failure = OpenAIRequestError(prefix+hint, status, reason, wait)
    if wait:
        with _lock:
            stamp = time.monotonic()
            for fingerprint in list(_blocked):
                if _blocked[fingerprint][0] <= stamp:
                    del _blocked[fingerprint]
            if len(_blocked) >= 128:
                del _blocked[next(iter(_blocked))]
            _blocked[identity(key)] = (stamp+wait, failure)
    return failure
