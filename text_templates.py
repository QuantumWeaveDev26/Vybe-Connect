"""Bounded text rendering adapted from OpenWA (MIT). See third_party/openwa/NOTICE.md."""
import re

PATTERN=re.compile(r'\{\{\s*([\w.-]+)\s*\}\}|\{(\w+)\}',re.ASCII)


def render(body,variables,limit=4000):
    # Determine size before allocation; unknown placeholders remain visible. Values are literal.
    cache={}
    for match in PATTERN.finditer(body):
        key=match[1] or match[2]
        if key not in cache:
            value=variables.get(key)
            cache[key]=str(value) if type(value) in (str,int,float,bool) else None
    size=len(body)
    for match in PATTERN.finditer(body):
        value=cache[match[1] or match[2]]
        if value is not None:size+=len(value)-len(match[0])
    if size>limit:raise ValueError('The personalized draft is too long. Shorten the macro or contact attribute.')
    return PATTERN.sub(lambda m:cache[m[1] or m[2]] if cache[m[1] or m[2]] is not None else m[0],body)


def contact_variables(contact):
    return dict(contact.get('attributes',{}),name=contact['name'])
