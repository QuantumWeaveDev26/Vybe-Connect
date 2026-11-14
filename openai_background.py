"""Official background Responses create/retrieve/cancel operations. No create retries."""
import json
import re
import urllib.request
import urllib.error
from openai_errors import ensure_available,http_failure
from agent_builder import agent_schema


def chat_schema():
    def obj(fields):return {'type':'object','properties':fields,'required':list(fields),'additionalProperties':False}
    string={'type':'string'}
    reference=obj({'label':string,'contact_id':string,'message_ids':{'type':'array','items':string}})
    knowledge=obj({'label':string,'document_id':string,'chunk_id':string})
    return obj({'answer':string,'references':{'type':'array','items':reference},'knowledge_references':{'type':'array','items':knowledge}})


def exchange(key,method,path,payload=None):
    if method=='POST' and not path:ensure_available(key)
    request=urllib.request.Request('https://api.openai.com/v1/responses'+path,data=json.dumps(payload).encode() if payload is not None else None,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method=method)
    try:
        with urllib.request.urlopen(request,timeout=30) as response:result=json.load(response)
    except urllib.error.HTTPError as e:raise http_failure(e,key,background=True) from None
    except Exception:raise ValueError('OpenAI background request outcome could not be confirmed.') from None
    if not isinstance(result,dict):raise ValueError('OpenAI returned an invalid background response.')
    return result


def response_path(id):
    if not isinstance(id,str) or not re.fullmatch(r'resp_[A-Za-z0-9_-]{1,200}',id):raise ValueError('Invalid provider response identifier.')
    return '/'+id


def openai_create(key,model,system,question,history):
    system+=' Return JSON with answer, references and knowledge_references. References must use only supplied contact IDs and message IDs. Knowledge references must use only document_id and chunk_id from supplied knowledge_passages. Include a short label for each. Use empty lists when no supplied evidence supports the answer. Do not invent sources.'
    payload={'model':model,'instructions':system,'input':history+[{'role':'user','content':question}],'background':True,'store':False,'max_output_tokens':2400,'text':{'format':{'type':'json_schema','name':'grounded_chat_answer','strict':True,'schema':chat_schema()}}}
    if model.startswith(('gpt-6','gpt-5')):payload['reasoning']={'effort':'none' if model=='gpt-6-luna' else 'low'}
    return exchange(key,'POST','',payload)


def openai_retrieve(key,id):return exchange(key,'GET',response_path(id))
def openai_cancel(key,id):return exchange(key,'POST',response_path(id)+'/cancel',{})


def openai_create_agent(key,model,system,question,history):
    payload={'model':model,'instructions':system,'input':history+[{'role':'user','content':question}],'background':True,'store':False,'max_output_tokens':2400,'text':{'format':{'type':'json_schema','name':'agent_proposal','strict':True,'schema':agent_schema()}}}
    if model.startswith(('gpt-6','gpt-5')):payload['reasoning']={'effort':'none' if model=='gpt-6-luna' else 'low'}
    return exchange(key,'POST','',payload)
