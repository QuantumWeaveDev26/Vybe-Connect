"""Bounded newest-first selection adapted from Chatwoot's MIT conversation formatter.

See third_party/chatwoot/NOTICE.md. Private notes and unverified outbound text stay out.
"""
def customer_conversation(messages,max_characters=8000):
    selected=[];used=0
    for message in reversed(messages):
        if message.get('direction') not in ('in','out') or message.get('private'):continue
        if 'status' in message and (message['direction']=='in' and message['status']!='received' or message['direction']=='out' and message['status'] not in ('accepted','sent','delivered','read')):continue
        body=message.get('body','')
        if not isinstance(body,str):continue
        text=body[:2000]
        if used+len(text)>max_characters:break
        selected.append({'direction':message['direction'],'text':text,'truncated':len(body)>len(text)})
        used+=len(text)
    return list(reversed(selected))
