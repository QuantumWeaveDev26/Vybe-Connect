"""OpenAI Responses API payloads. No SDK, tool execution, or automatic retries."""
import json
import urllib.request
import urllib.error


def findings_schema():
    def obj(properties):return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
    string={'type':'string'}
    actions=[{'type':'null'}]
    for kind,key in [('tag','tag'),('assign','owner'),('note','body'),('draft_reply','body'),('task','title')]:
        actions.append(obj({'type':{'type':'string','enum':[kind]},key:string}))
    finding=obj({'title':string,'details':string,'contact_id':string,'evidence_ids':{'type':'array','items':string},'action':{'anyOf':actions}})
    return obj({'summary':string,'findings':{'type':'array','items':finding}})


def request_openai(key,model,system,question,history,structured=False,schema=None):
    payload={'model':model,'instructions':system,'input':history[-12:]+[{'role':'user','content':question}],'store':False,'max_output_tokens':4000 if structured else 1600}
    if model.startswith(('gpt-6','gpt-5')):payload['reasoning']={'effort':'none' if model=='gpt-6-luna' else 'low'}
    if structured:payload['text']={'format':{'type':'json_schema','name':'workspace_findings','strict':True,'schema':findings_schema()}}
    if schema is not None:payload.update(max_output_tokens=2400,text={'format':{'type':'json_schema','name':'customer_reply','strict':True,'schema':schema}})
    request=urllib.request.Request('https://api.openai.com/v1/responses',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(request,timeout=90) as response:result=json.load(response)
    except urllib.error.HTTPError as e:raise ValueError('OpenAI returned HTTP '+str(e.code)+'. Verify server credentials, model access and API billing. No automatic retry was attempted.') from None
    except Exception:raise ValueError('OpenAI did not return a usable response. Check connectivity and API status. No automatic retry was attempted.') from None
    if not isinstance(result,dict) or result.get('status')!='completed':raise ValueError('OpenAI did not complete this response. No findings were generated from partial output.')
    content=[]
    output=result.get('output',[])
    if not isinstance(output,list):raise ValueError('OpenAI returned invalid output content.')
    for item in output:
        if not isinstance(item,dict) or item.get('type')!='message':continue
        parts=item.get('content',[])
        if not isinstance(parts,list) or any(not isinstance(part,dict) for part in parts):raise ValueError('OpenAI returned invalid message content.')
        for part in parts:
            if part.get('type')=='refusal':raise ValueError('OpenAI declined this request. No findings were generated.')
            if part.get('type')=='output_text' and isinstance(part.get('text'),str):content.append(part['text'])
    text='\n'.join(content).strip()
    if not text:raise ValueError('OpenAI returned no text answer.')
    if len(text)>20000:raise ValueError('OpenAI returned an oversized answer. Reduce the requested analysis.')
    return text
