"""Bounded newest-first selection adapted from Chatwoot's MIT conversation formatter.

See third_party/chatwoot/NOTICE.md. Private notes and unverified outbound text stay out.
"""
import json


def analysis_context(context,max_bytes=22000):
    """Keep evidence intact while reducing optional samples to the included input budget."""
    for key in ('knowledge_sources','templates'):
        for item in context.get(key,[]):
            body=item.get('body','')
            if isinstance(body,str) and len(body)>750:
                item['body']=body[:750];item['body_truncated']=True
    context['input_scope']='Reference bodies may be excerpted; input-size limits may further reduce the recent conversation and configuration samples. Only supplied evidence is available.'
    collections=('recent_conversations','knowledge_sources','knowledge_passages','templates','campaigns','automation_configuration','team_members')
    def size(value):return len(json.dumps(value,ensure_ascii=False).encode('utf-8'))
    while size({k:v for k,v in context.items() if not k.startswith('_')})>max_bytes:
        # Retain the first (newest) item of each category where possible.
        candidates=[key for key in collections if len(context.get(key,[]))>1]
        if not candidates:candidates=[key for key in collections if context.get(key)]
        if not candidates:raise ValueError('Agent instructions and workspace facts exceed the analysis input limit. Shorten the agent instructions.')
        key=max(candidates,key=lambda key:size(context[key][-1]));context[key].pop()
    return context


def conversation_evidence(message):
    return (not message.get('private') and
            (message.get('direction')=='in' and message.get('status')=='received' or
             message.get('direction')=='out' and message.get('status') in ('accepted','sent','delivered','read')))


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
