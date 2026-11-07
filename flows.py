"""Bounded local flow graph: no external actions and no executable expressions."""
import copy
import re
import time
import json

TYPES={'message','question','condition','tag','status','handoff','wait','attribute','untag','assign','media','template','webhook'}


class FlowExecutionError(ValueError):pass


def validate_members(graph,member_ids):
    if any(n['type']=='assign' and n['member_id'] not in member_ids for n in graph['nodes']):raise FlowExecutionError('A configured teammate no longer has workspace access.')


def default_graph(reply):
    return {'start':'welcome','nodes':[{'id':'welcome','type':'message','text':reply,'next':'team'},{'id':'team','type':'handoff'}]}


def validate_graph(graph):
    if not isinstance(graph,dict) or not isinstance(graph.get('nodes'),list) or not 1<=len(graph['nodes'])<=50: raise ValueError('A flow needs 1–50 nodes.')
    graph=copy.deepcopy(graph); nodes=graph['nodes']; ids=[n.get('id') for n in nodes if isinstance(n,dict)]
    if len(ids)!=len(nodes) or len(set(ids))!=len(ids) or any(not isinstance(i,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,60}',i) for i in ids): raise ValueError('Each node needs a unique, short id.')
    if graph.get('start') not in ids: raise ValueError('Choose a valid start node.')
    for n in nodes:
        if n.get('type') not in TYPES: raise ValueError('Unsupported node type.')
        if n['type'] in ['message','question'] and (not isinstance(n.get('text'),str) or not n['text'].strip() or len(n['text'])>4096): raise ValueError('Message and question nodes need text (up to 4,096 characters).')
        if n['type']=='question' and not re.fullmatch(r'[a-zA-Z]\w{0,49}',str(n.get('variable',''))): raise ValueError('Question variables use letters, numbers and underscores, starting with a letter.')
        if n['type']=='condition' and (not isinstance(n.get('field'),str) or not isinstance(n.get('value'),str) or len(n['field'])>50 or len(n['value'])>200): raise ValueError('A condition needs a field and text value.')
        if n['type'] in ['tag','untag'] and (not isinstance(n.get('tag'),str) or not n['tag'].strip() or len(n['tag'])>60): raise ValueError('Tag nodes need a tag of up to 60 characters.')
        if n['type']=='attribute' and (not isinstance(n.get('field'),str) or not re.fullmatch(r'[A-Za-z0-9_ -]{1,60}',n['field']) or not isinstance(n.get('value'),str) or len(n['value'])>1000):raise ValueError('Attribute nodes need a bounded custom field name and a value of up to 1,000 characters.')
        if n['type']=='assign' and (not isinstance(n.get('member_id'),str) or not 1<=len(n['member_id'])<=64):raise ValueError('Assignment nodes need a workspace teammate.')
        if n['type'] in ['media','template']:
            key='asset_id' if n['type']=='media' else 'template_id'
            if not isinstance(n.get(key),str) or not 1<=len(n[key])<=64:raise ValueError('Select a workspace attachment or template.')
        if n['type']=='media' and (not isinstance(n.get('caption',''),str) or len(n.get('caption',''))>1024):raise ValueError('Use a chatbot caption up to 1,024 characters.')
        if n['type']=='status' and n.get('status') not in ['open','pending','solved']: raise ValueError('Invalid node status.')
        if n['type']=='webhook' and (not isinstance(n.get('url'),str) or not n['url'].startswith(('http://','https://')) or len(n['url'])>2048):raise ValueError('Webhook nodes need an HTTP or HTTPS URL (up to 2,048 characters).')
        if n['type']=='wait' and (type(n.get('seconds')) is not int or not 1<=n['seconds']<=604800):raise ValueError('Wait duration must be 1–604,800 whole seconds.')
        for key in ['next','yes','no']:
            if n.get(key) and n[key] not in ids: raise ValueError('A connection points to a missing node.')
    index={n['id']:n for n in nodes}; done=set(); visiting=set()
    def visit(id):
        if id in visiting: raise ValueError('Flow loops are not supported. Remove the circular connection.')
        if id in done: return
        visiting.add(id)
        for k in ['next','yes','no']:
            if index[id].get(k): visit(index[id][k])
        visiting.remove(id);done.add(id)
    for id in ids: visit(id)
    return graph


def run_graph(flow,contact,incoming,resume=False,timer=False,timestamp=None,member_ids=None,execution='draft',delivered=False,resources=None):
    c=copy.deepcopy(contact); graph=flow['graph']; nodes={n['id']:n for n in graph['nodes']}; messages=[]
    validate_members(graph,set(member_ids or []))
    stamp=int(time.time()) if timestamp is None else timestamp
    c.setdefault('attributes',{}); c.setdefault('tags',[])
    def render(text):
        return re.sub(r'\{\{\s*([a-zA-Z]\w*)\s*\}\}',lambda m:str(c['name'] if m[1]=='name' else c['attributes'].get(m[1],'')),text)
    id=graph['start']
    if resume:
        session=c.get('flow_session',{});previous=nodes.get(session.get('node_id'))
        if session.get('version',0)!=flow.get('version',0) or not previous:c.pop('flow_session',None);return c,[]
        if session.get('mode')=='sending':
            if not delivered:raise FlowExecutionError('A newer customer message arrived before the chatbot prompt was accepted. Review the conversation.')
            if previous['type']=='question':
                c['flow_session']=dict(session,mode='question');c['flow_session'].pop('send_id',None);return c,[]
        elif previous['type']=='wait':
            if not timer or session.get('due',stamp+1)>stamp:return c,[]
        elif previous['type']=='question' and not timer:c['attributes'][previous['variable']]=incoming[:1000]
        else:c.pop('flow_session',None);return c,[]
        id=previous.get('next')
    c.pop('flow_session',None)
    for _ in range(50):
        if not id: break
        n=nodes[id]; kind=n['type']
        if kind in ['message','question']:
            body=render(n['text'])
            if len(body)>4096:raise FlowExecutionError('Expanded message exceeds the supported size.')
            messages.append(body)
            if execution=='live':
                c['flow_session']={'flow_id':flow['id'],'node_id':id,'mode':'sending','execution':'live','version':flow.get('version',0)};break
            if kind=='question':
                c['flow_session']={'flow_id':flow['id'],'node_id':id,'mode':'question','execution':execution,'version':flow.get('version',0)}
                break
        elif kind in ['media','template']:
            resource=(resources or {}).get(id)
            if not resource:raise FlowExecutionError('Chatbot media or template dependency is unavailable.')
            if kind=='media':
                caption=render(n.get('caption',''))
                if len(caption)>1024:raise FlowExecutionError('Expanded media caption exceeds 1,024 characters.')
                body='['+resource['media_kind']+'] '+resource['filename']+('\n'+caption if caption else '')
                payload={'caption':caption}
            else:body=re.sub(r'\{\{\s*(?:name|1)\s*\}\}',lambda _:c['name'],resource['template'].get('body',''));payload={}
            if len(body)>4096:raise FlowExecutionError('Expanded template or attachment preview exceeds the supported size.')
            messages.append(body)
            if execution=='live':
                c['flow_session']={'flow_id':flow['id'],'node_id':id,'mode':'sending','execution':'live','version':flow.get('version',0),'delivery_payload':payload};break
        elif kind=='wait':
            c['flow_session']={'flow_id':flow['id'],'node_id':id,'mode':'wait','execution':execution,'version':flow.get('version',0),'due':stamp+n['seconds']}
            break
        elif kind=='condition':
            value=c['name'] if n['field']=='name' else c['attributes'].get(n['field'],'')
            id=n.get('yes') if str(value).strip().lower()==n['value'].strip().lower() else n.get('no')
            continue
        elif kind=='tag':
            if n['tag'].casefold() not in {tag.casefold() for tag in c['tags']}:c['tags'].append(n['tag'])
        elif kind=='untag':c['tags']=[tag for tag in c['tags'] if tag.casefold()!=n['tag'].casefold()]
        elif kind=='attribute':
            value=render(n['value'])
            if len(value)>1000:raise FlowExecutionError('Expanded attribute value exceeds the supported size.')
            c['attributes'][n['field']]=value
        elif kind=='assign':c['assignee']=n['member_id']
        elif kind=='webhook':
            if n.get('save_to'):c['attributes'][n['save_to']]='ok'
        elif kind=='status': c['status']=n['status']
        elif kind=='handoff': c['status']='pending';c['automation_hold']=True;c.pop('outgoing_watch',None);break
        id=n.get('next')
    if len(c['tags'])>25 or len(c['attributes'])>50 or len(json.dumps(c['attributes']))>10000:raise FlowExecutionError('Contact tag or attribute capacity exceeded.')
    return c,messages
