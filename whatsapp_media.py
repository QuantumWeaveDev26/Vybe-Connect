"""Server-only, ID-based WhatsApp Cloud API media upload and sending.

No retries, URL downloads, persistence, or delivery claims live here.
"""
import http.client
import json
import re
import secrets
import urllib.error
import urllib.request

from meta import ProviderError, settings


MAX_MEDIA_BYTES = 5 * 1024 * 1024
SUPPORTED_TYPES = {
    'image/jpeg': ('image', ('.jpg', '.jpeg')),
    'image/png': ('image', ('.png',)),
    'audio/ogg': ('audio', ('.ogg', '.opus')),
    'audio/mpeg': ('audio', ('.mp3', '.mpeg')),
    'video/mp4': ('video', ('.mp4',)),
    'application/pdf': ('document', ('.pdf',)),
}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward a workspace credential to a redirect target.
        return None


_open = urllib.request.build_opener(_NoRedirect()).open


def _fail(message):
    raise ProviderError(message, True)


def _configuration(tenant):
    if not isinstance(tenant, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', tenant):
        _fail('Invalid workspace identifier.')
    return settings(tenant)


def _configured(s):
    return bool(s.get('TOKEN') and not any(ord(c) < 32 or ord(c) == 127 for c in s['TOKEN'])
                and re.fullmatch(r'[0-9]{1,128}', s.get('PHONE_ID', ''))
                and re.fullmatch(r'v[0-9]+\.[0-9]+', s.get('VERSION', '')))


def media_status(tenant):
    """Return local configuration/capabilities only, never credentials."""
    s = _configuration(tenant)
    return {'configured': _configured(s), 'live': s.get('LIVE', '').lower() == 'true',
            'max_bytes': MAX_MEDIA_BYTES, 'supported_types': dict((mime, value[0]) for mime, value in SUPPORTED_TYPES.items())}


def _filename(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 ._-]{0,119}', value) or '..' in value or value.endswith((' ', '.')):
        _fail('Use a plain filename of 1–120 ASCII letters, digits, spaces, dots, dashes or underscores, without paths.')
    return value


def _validate_file(filename, content_type, data):
    _filename(filename)
    if not isinstance(content_type, str) or content_type not in SUPPORTED_TYPES:
        _fail('Unsupported media MIME type.')
    if not filename.lower().endswith(SUPPORTED_TYPES[content_type][1]):
        _fail('The filename extension must match the media MIME type.')
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_MEDIA_BYTES:
        _fail('Media must be nonempty bytes, at most 5 MiB.')
    valid = False
    if content_type == 'image/jpeg':valid = data.startswith(b'\xff\xd8\xff')
    elif content_type == 'image/png':valid = data.startswith(b'\x89PNG\r\n\x1a\n')
    elif content_type == 'application/pdf':valid = data.startswith(b'%PDF-')
    elif content_type == 'audio/mpeg':valid = data.startswith(b'ID3') or (len(data) > 1 and data[0] == 255 and data[1] & 0xe0 == 0xe0)
    elif content_type == 'video/mp4':valid = len(data) >= 12 and data[4:8] == b'ftyp'
    elif content_type == 'audio/ogg':
        # Opus identification header, with a single channel. No Vorbis/base OGG.
        header = data.find(b'OpusHead', 0, min(len(data), 512))
        valid = data.startswith(b'OggS') and header >= 28 and len(data) >= header + 19 and data[header+9] == 1
    if not valid:_fail('Media bytes do not match the supported format (OGG requires mono Opus).')


def _request(s, edge, body, content_type):
    if not _configured(s):_fail('Configure the Meta token, numeric phone ID and Graph API version on the server first.')
    request = urllib.request.Request(
        'https://graph.facebook.com/' + s['VERSION'] + '/' + s['PHONE_ID'] + '/' + edge,
        data=body, headers={'Authorization':'Bearer ' + s['TOKEN'], 'Content-Type':content_type}, method='POST')
    try:
        with _open(request, timeout=25) as response:
            raw = response.read(65537)
        if len(raw) > 65536:raise ValueError('Response too large')
        result = json.loads(raw)
        if not isinstance(result, dict) or 'error' in result:raise ValueError('Unexpected result')
        return result
    except urllib.error.HTTPError as error:
        # Do not echo provider error text, credentials, customer data or URLs.
        # Redirects, timeouts, and server failures leave the outcome uncertain.
        raise ProviderError('Meta media request rejected (HTTP ' + str(error.code) + ').', 400 <= error.code < 500 and error.code != 408) from None
    except (OSError, http.client.HTTPException, ValueError, UnicodeError):
        raise ProviderError('The provider result is uncertain. Check Meta before retrying.') from None


def upload_media(tenant, filename, content_type, data):
    """Upload bytes; return Meta media ID. Does not send a WhatsApp message.

    Uses credentials regardless of LIVE; callers must authorize uploads separately.
    """
    s = _configuration(tenant)
    _validate_file(filename, content_type, data)
    boundary = 'teamwave_' + secrets.token_hex(24)
    while boundary.encode() in data:boundary = 'teamwave_' + secrets.token_hex(24)
    parts = []
    for name, value in [('messaging_product', 'whatsapp'), ('type', content_type)]:
        parts.append(('--' + boundary + '\r\nContent-Disposition: form-data; name="' + name + '"\r\n\r\n' + value + '\r\n').encode('ascii'))
    # Filename and MIME passed strict ASCII allowlists before reaching headers.
    parts.append(('--' + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="' + filename + '"\r\nContent-Type: ' + content_type + '\r\n\r\n').encode('ascii'))
    parts.extend([data, ('\r\n--' + boundary + '--\r\n').encode('ascii')])
    result = _request(s, 'media', b''.join(parts), 'multipart/form-data; boundary=' + boundary)
    media_id = result.get('id')
    if not isinstance(media_id, str) or not re.fullmatch(r'[0-9]{1,128}', media_id):
        raise ProviderError('Meta returned no valid media ID; upload outcome is uncertain.')
    return media_id


def send_media(tenant, phone, media_id, kind, caption='', filename=''):
    """Send uploaded media by ID, returning acceptance ID, not delivery proof.

    Caller must enforce workspace ownership, consent and service-window policy.
    """
    s = _configuration(tenant)
    if s.get('LIVE', '').lower() != 'true':_fail('Live sending is disabled in the server environment.')
    if not isinstance(phone, str) or not re.fullmatch(r'\+?[1-9][0-9]{6,14}', phone):_fail('Use an international recipient phone number.')
    if not isinstance(media_id, str) or not re.fullmatch(r'[0-9]{1,128}', media_id):_fail('Use a numeric uploaded Meta media ID.')
    if not isinstance(kind, str) or kind not in ('image', 'audio', 'video', 'document'):_fail('Unsupported media message kind.')
    if not isinstance(caption, str) or len(caption) > 1024 or '\x00' in caption:_fail('Media captions support at most 1,024 characters.')
    if not isinstance(filename, str):_fail('Filename must be text.')
    if caption and kind == 'audio':_fail('Audio messages cannot have captions.')
    if filename and kind != 'document':_fail('A display filename is supported only for documents.')
    item = {'id': media_id}
    if caption:item['caption'] = caption
    if filename:item['filename'] = _filename(filename)
    payload = {'messaging_product':'whatsapp', 'recipient_type':'individual', 'to':phone.lstrip('+'), 'type':kind, kind:item}
    result = _request(s, 'messages', json.dumps(payload).encode('utf-8'), 'application/json')
    try:message_id = result['messages'][0]['id']
    except (KeyError, IndexError, TypeError):message_id = None
    if not isinstance(message_id, str) or not re.fullmatch(r'[A-Za-z0-9_.=+/-]{1,512}', message_id):
        raise ProviderError('Meta returned no valid message ID; send outcome is uncertain.')
    return message_id
